"""Business spending ledger: categorise every bank/card transaction, match stock payments to purchases
and raise questions for anything unclear. Learns from the user's answers (merchant -> category).

Categories are the ones the user chose (business basics, overheads, travel & food) plus Transfers / Other.
Answers live in bank_answers.json: {"txn": {txn_id: category}, "rules": {merchant_key: category}}.
"""
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from spapi import load_env

ROOT = Path(__file__).parent
ANSWERS = ROOT / "bank_answers.json"
# Transfers from your own limited company (its name on bank statements, from .env)
_OWN = load_env().get("OWN_COMPANY_NAME", "").strip().lower()
OWN_COMPANY_RX = (f"|^from {re.escape(_OWN)}|{re.escape(_OWN)}" if _OWN else "")

CATEGORIES = ["Stock", "Prep fees", "Shipping & postage", "Amazon fees", "Amazon payouts", "Refunds",
              "Software & subscriptions", "Phone & internet", "Accountant", "Bank fees",
              "Fuel", "Train", "Parking", "Meals", "Transfers", "Other / not sure"]

STORES = r"amazon|amzn|currys|argos|b&q|diy\.com|tradepoint|john ?lewis|costco|superdrug|boots|lookfantastic|very\.co|ebuyer|toolstation|screwfix|game digital|game\.co|harvey ?norman|sports ?direct|a1 ?tech|approved ?food|lloyds ?pharmacy|awd-?it|scan computers|box\.co|ao\.com|wilko|smyths|the entertainer|tesco|asda|sainsbury|morrisons|home ?bargains|b&m|aldi|lidl|b ?q limited|tendr|garmin|egift|gift ?card|selfridges|pokemon center|perfumesclub|allbeauty|zatu|sharkninja|central computers|crampton|jarrold|everup|very\b|next\b|tassimo|harrods|notino|feelunique|cult beauty|space nk|boots|hamleys|lego|nintendo|currys business|amazon business|ebay|paypal \*amazon"
RULES = [  # (regex on merchant + description, category, money direction: "out"/"in"/None)
    (r"amazon (eu|payments)|amzn mktp payout|amazon\.co\.uk.*(settlement|disbursement)|amazon services europe", "Amazon payouts", "in"),
    (r"amazon (seller|selling|fba)|seller ?fees|amazon advertising|amzn ads", "Amazon fees", "out"),
    (STORES, "Refunds", "in"),
    (STORES, "Stock", "out"),
    (r"prep|fulfil|3pl|warehouse", "Prep fees", "out"),
    (r"royal ?mail|parcelforce|evri|hermes|dpd|\bups\b|fedex|dhl|yodel|inpost|parcel2go|packlink|post office", "Shipping & postage", "out"),
    (r"invenno|keepa|selleramp|\bsas\b|discord|anthropic|claude|openai|chatgpt|google|microsoft|adobe|shopify|netlify|arbisource|dbh ?deals|"
     r"dbh ?deal|reclaimhq|tactical ?arbitrage|jungle ?scout|helium|canva|notion|zoom|dropbox|icloud|apple\.com/bill|patreon|whop|livecops|airtable|tailscale|truelayer", "Software & subscriptions", "out"),
    (r"\bee\b|vodafone|\bo2\b|three\.co|\bthree\b|\bbt\b|sky (digital|broadband)|virgin media|giffgaff|tesco mobile|id mobile|hyperoptic|plusnet|talktalk", "Phone & internet", "out"),
    (r"accountan|accounting|bookkeep|intuit|qbooks|xero|quickbooks|freeagent|crunch|companies house", "Accountant", "out"),
    (r"\bfee\b|fees|interest|charge|annual fee|late payment|fx fee|non-sterling", "Bank fees", "out"),
    (r"shell|\bbp\b|esso|texaco|jet petrol|gulf|sainsbury.?s petrol|tesco petrol|asda petrol|fuel|petrol", "Fuel", "out"),
    (r"trainline|\btfl\b|transport for london|lner|gwr|avanti|southern rail|thameslink|c2c|greater anglia|southeastern|national rail|uber(?! eats)|bolt\.eu|addison lee", "Train", "out"),
    (r"ncp|ringgo|paybyphone|justpark|parking|apcoa|q-park|euro car parks", "Parking", "out"),
    (r"pret|mcdonald|costa|starbucks|greggs|deliveroo|uber ?eats|just ?eat|nando|kfc|subway|wagamama|five guys|leon|itsu|caffe nero|burger king|domino|pizza|restaurant|cafe|coffee", "Meals", "out"),
    (r"transfer|payment received|direct debit payment|repayment|thank you for your payment|top.?up|to savings|from savings|save the change|"
     r"^to american exp|american express|^to capital on tap|capital on tap|money added from|payment made \(|exchanged to" + OWN_COMPANY_RX, "Transfers", None),
]


def load_answers():
    try:
        return json.loads(ANSWERS.read_text(encoding="utf-8"))
    except Exception:
        return {"txn": {}, "rules": {}}


def merchant_key(t):
    """Stable key for 'the same merchant' so one answer covers future payments.
    Drops payment-processor prefixes (PAYPAL *, SP ), towns after double spaces and reference codes with digits."""
    s = (t.get("merchant") or t.get("description") or "").lower().strip()
    s = re.split(r"\s{2,}", s)[0]                                         # Amex: "MERCHANT     TOWN"
    s = re.sub(r"^(paypal|sp|sq|sumup|zettle|izettle|stripe|gc|pp)\s*\*\s*", "", s)   # PAYPAL *B Q LIMITED -> b q limited
    s = " ".join(w for w in re.split(r"[\s*]+", s) if not re.search(r"\d", w))      # drop codes like BT7LQ09S4
    s = re.sub(r"[^a-z& ]+", " ", s)
    words = [w for w in s.split() if len(w) > 1 and w not in {"ltd", "limited", "uk", "gb", "london", "www", "com", "co"}]
    return " ".join(words[:3]) or s.strip()[:20]


def answer(txn_id, category, merchant=None, remember=True):
    a = load_answers()
    a["txn"][txn_id] = category
    if remember and merchant:
        a["rules"][merchant] = category
    ANSWERS.write_text(json.dumps(a, indent=1, ensure_ascii=False), encoding="utf-8")
    return a


def categorise(t, answers):
    if t["id"] in answers["txn"]:
        return answers["txn"][t["id"]], "you"
    mk = merchant_key(t)
    if mk in answers["rules"]:
        return answers["rules"][mk], "learned"
    text = f"{t.get('merchant', '')} {t.get('description', '')}".lower()
    direction = "in" if (t.get("amount") or 0) > 0 else "out"
    for rx, cat, d in RULES:
        if (d is None or d == direction) and re.search(rx, text, re.I):
            return cat, "rule"
    return None, None

NICE = [  # merchant text -> store name shown on the tracker
    (r"amazon\.de|amazon de", "Amazon DE"), (r"amazon\.it|amazon it", "Amazon IT"), (r"amazon\.fr|amazon fr", "Amazon FR"),
    (r"amazon\.es|amazon es", "Amazon ES"), (r"amazon business", "Amazon Business"), (r"amazon eu sarl|www\.amazon\b(?!\.co)", "Amazon EU"),
    (r"amazon|amzn", "Amazon UK"), (r"currys", "Currys"), (r"argos", "Argos"), (r"b ?& ?q|b q limited|diy\.com", "B&Q"),
    (r"tradepoint", "TradePoint"), (r"john ?lewis", "John Lewis"), (r"costco", "Costco"), (r"\bvery\b", "Very"), (r"ebay", "eBay"),
    (r"selfridges", "Selfridges"), (r"lookfantastic", "Lookfantastic"), (r"superdrug", "Superdrug"), (r"boots", "Boots"),
    (r"smyths", "Smyths"), (r"screwfix", "Screwfix"), (r"toolstation", "Toolstation"), (r"ebuyer", "Ebuyer"), (r"a1 ?tech|omnibytes", "A1Techdeals"),
    (r"sharkninja", "SharkNinja"), (r"garmin", "Garmin"), (r"tassimo", "Tassimo"), (r"pokemon center", "Pokémon Center"),
    (r"perfumesclub", "PerfumesClub"), (r"hsamuel|h samuel", "H Samuel"), (r"sgs-?engineering", "SGS Engineering"),
    (r"baby mori", "Mori"), (r"fragrance shop", "The Fragrance Shop"), (r"playstation", "PlayStation Store"), (r"allbeauty", "allbeauty"), (r"tk ?maxx|tendr", "TK Maxx"), (r"harvey ?norman", "Harvey Norman"),
]


def store_name(t):
    text = f"{t.get('merchant', '')} {t.get('description', '')}".lower()
    for rx, name in NICE:
        if re.search(rx, text):
            return name
    raw = re.split(r"\s{2,}| - ", (t.get("merchant") or t.get("description") or "").strip())[0]
    raw = re.sub(r"^(paypal|sp|sq|sumup)\s*\*\s*", "", raw, flags=re.I)
    raw = re.sub(r"\b(ltd|limited|uk|online|www\.|\.com|\.co\.uk)\b", "", raw, flags=re.I).strip(" .*-")
    return raw.title()[:30] or "Unknown"


def _eur_ok(gbp, eur):
    return 0.80 * eur <= gbp <= 0.93 * eur      # EUR orders on GBP cards (rate + card FX fee)


def _site_rx(source):
    s = source.lower()
    if s.startswith("amazon"):
        return r"amazon|amzn"
    return re.escape(s.split()[0])


def match_purchases(cards, txns):
    """Attach a payment to each purchase card; flag charged twice / not charged / cancelled-but-charged."""
    debits = [t for t in txns if (t.get("amount") or 0) < 0]
    credits = [t for t in txns if (t.get("amount") or 0) > 0]
    used = set()
    today = date.today()
    same = {}
    for c in cards:  # identical orders (same site + total) placed close together
        if c.get("total"):
            same.setdefault((c["source"], round(float(c["total"]), 2)), []).append(datetime.fromisoformat(c["orderedAt"][:10]).date())
    for c in cards:
        c.pop("payment", None)
        c["problems"] = [p for p in c.get("problems", []) if p.get("type") != "money"]
        if c.get("source") == "Invenno" or c.get("store") or c.get("total") in (None, 0):
            continue
        total, cur = float(c["total"]), c.get("currency") or "£"
        od = datetime.fromisoformat(c["orderedAt"][:10]).date()
        rx = _site_rx(c["source"])
        hits = []
        for t in debits:
            if t["id"] in used:
                continue
            td = datetime.fromisoformat(t["date"]).date()
            if not (od - timedelta(days=1) <= td <= od + timedelta(days=14)):
                continue
            if not re.search(rx, f"{t.get('merchant', '')} {t.get('description', '')}", re.I):
                continue
            amt = abs(t["amount"])
            if cur == "€" and t.get("origCurrency") == "EUR":
                ok = abs(abs(t.get("origAmount") or 0) - total) < 0.02      # exact euro amount from the card statement
            elif cur == "€":
                ok = not t.get("origCurrency") and _eur_ok(amt, total)   # only guess the FX when the statement has no original amount
            else:
                ok = t.get("origCurrency", "GBP") in ("GBP", "") and abs(amt - total) < 0.02
            if ok:
                hits.append(t)
        if hits:
            t = hits[0]
            used.add(t["id"])
            c["payment"] = {"amount": abs(t["amount"]), "date": t["date"], "source": t["source"], "txn": t["id"]}
            twins = sum(1 for d in same.get((c["source"], round(total, 2)), []) if abs((d - od).days) <= 14)
            if len(hits) > twins:
                c.setdefault("problems", []).append({"type": "money", "text": f"{len(hits)} payments of £{abs(t['amount']):.2f} but {twins} order email{'s' if twins > 1 else ''}: a duplicate charge, or another order from an inbox I can't read?"})
            if c.get("cancelled"):
                refunded = any(re.search(rx, f"{r.get('merchant', '')} {r.get('description', '')}", re.I) and abs(r["amount"] - abs(t["amount"])) < 0.02
                               and r["date"] >= t["date"] for r in credits)
                if not refunded:
                    c.setdefault("problems", []).append({"type": "money", "text": f"Cancelled but charged £{abs(t['amount']):.2f}, no refund seen yet"})
        elif not c.get("cancelled") and c.get("stage") not in ("ordered",) and (today - od).days > 10:
            c.setdefault("problems", []).append({"type": "money", "text": "No card payment found for this order"})

    # Purchases known only from Invenno: the card payment tells us the store
    for c in cards:
        if c.get("source") != "Invenno" and not c.get("store"):
            continue
        p = c.get("inv") or {}
        total = round(float(c.get("total") or 0), 2)
        if total <= 0:
            continue
        od = datetime.fromisoformat(c["orderedAt"][:10]).date()
        cands = [t for t in debits if t["id"] not in used and abs(abs(t["amount"]) - total) < 0.02
                 and od - timedelta(days=4) <= datetime.fromisoformat(t["date"]).date() <= od + timedelta(days=7)]
        cands.sort(key=lambda t: abs((datetime.fromisoformat(t["date"]).date() - od).days))
        if cands:
            t = cands[0]
            used.add(t["id"])
            c["store"] = store_name(t)
            c["source"] = c["store"]
            c["payment"] = {"amount": abs(t["amount"]), "date": t["date"], "source": t["source"], "txn": t["id"]}
        elif p.get("a2a"):
            c["store"] = c["source"] = "Amazon EU (A2A)"
    return used


def build(bank_data, purchase_cards):
    """Categorised ledger + questions + spend summary."""
    answers = load_answers()
    txns = [dict(t) for t in (bank_data.get("transactions") or [])]
    used = match_purchases(purchase_cards, txns)
    by_txn = {c["payment"]["txn"]: c for c in purchase_cards if c.get("payment")}
    questions, seen_q = [], set()
    for t in txns:
        cat, how = categorise(t, answers)
        t["merchantKey"] = merchant_key(t)
        o = by_txn.get(t["id"])
        if o:
            t["order"] = f"{o['source']} {o.get('order') or ''} · {o['qty']}× {o['title'][:60]}".strip()
            cat, how = cat or "Stock", how or "matched"
        t["cat"], t["catHow"] = cat, how
        q = None
        if not cat:
            name = re.split(r"\s{2,}| - ", (t.get("merchant") or t.get("description") or "").strip())[0]
            name = re.sub(r"\s+\d{6,}$", "", name).strip()
            q = f"What was this {'payment to' if t['amount'] < 0 else 'money from'} {name} for?"
        elif cat == "Stock" and not o and t["amount"] < 0:
            t["note"] = "Stock, no matching order email (bought from an inbox I can't read yet?)"
        t["question"] = q
        if q and t["merchantKey"] not in seen_q:
            seen_q.add(t["merchantKey"])   # one question per merchant; the answer is remembered for the rest
            questions.append({k: t.get(k) for k in ("id", "date", "amount", "currency", "description", "merchant", "source", "merchantKey", "question", "cat")})
    out = [t for t in txns if t["amount"] < 0]
    spend = {}
    for t in out:
        spend[t["cat"] or "Uncategorised"] = round(spend.get(t["cat"] or "Uncategorised", 0) + abs(t["amount"]), 2)
    months = {}
    for t in out:
        m = t["date"][:7]
        months.setdefault(m, {})
        k = t["cat"] or "Uncategorised"
        months[m][k] = round(months[m].get(k, 0) + abs(t["amount"]), 2)
    return {"transactions": txns, "questions": questions, "spendByCategory": dict(sorted(spend.items(), key=lambda x: -x[1])),
            "spendByMonth": months, "categories": CATEGORIES, "matched": len(used)}
