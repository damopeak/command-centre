"""Purchases tracker: every order from "ordered" to "live at Amazon".

Sources (all read-only):
  * Order emails in the connected inboxes (GMAIL_n / ICLOUD_n): Amazon UK/DE/FR/IT/ES (+ Business), Currys,
    John Lewis, Costco and others -> ordered / dispatched / out for delivery / delivered / cancelled / delayed,
    with order number, item, quantity, total, delivery town (PREP_TOWN = prep, HOME_TOWN = home, from .env).
  * Invenno purchases (logged by the user's Google Sheet export) -> prep centre parcel status
    (received / prepped / missing / Needs Attention), units sent to Amazon, live stock.
Problems: cancelled, units missing / needs attention, stuck (relaxed limits), order email with no Invenno purchase.
Payment-declined emails are ignored on purpose (the user just updates the card).
"""
import email
import email.utils
import imaplib
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import important
import invenno
import otp_watch
from spapi import load_env, uk_offset

ROOT = Path(__file__).parent
MAIL_CACHE = ROOT / "purchases_mail_cache.json"   # parsed emails by Message-ID (bodies are only fetched once)
STATE = ROOT / "purchases_state.json"             # which problems were already posted to Discord
NOTES = ROOT / "purchase_notes.json"              # the user's notes per order: {key: {"text", "at"}} (synced with the sheet)
DAYS = 30
STUCK = {"eu_delivery": 14, "uk_delivery": 7, "prep": 7, "send_in": 14}   # "Relaxed", chosen by the user

SENDER_TERMS = ["amazon.co.uk", "amazon.de", "amazon.fr", "amazon.it", "amazon.es", "amazon.nl", "amazon.com",
                "currys", "johnlewis", "costco", "argos", "diy.com", "tradepoint", "very.co.uk", "ebuyer",
                "game.co.uk", "boots", "superdrug", "lookfantastic", "harveynorman", "sportsdirect", "toolstation",
                "screwfix", "awd-it", "a1techdeals", "approvedfood", "lloydspharmacy", "dpd.co.uk"]

AMZ_KIND = [
    ("cancelled", re.compile(r"^(items? cancell?ed|artikel storniert|storniert|article annulé|articles? annulés?|annullat|cancelad)", re.I)),
    ("ordered", re.compile(r"^(ordered|bestellt|commandé|ordinato|pedido|besteld|pending verification)\b", re.I)),
    ("shipped", re.compile(r"^(dispatched|shipped|versendet|expédié|spedito|enviado|verzonden)\b", re.I)),
    ("out", re.compile(r"^(out for delivery|in zustellung|en cours de livraison|in consegna|en reparto)\b", re.I)),
    ("delivered", re.compile(r"^(delivered|zugestellt|livré|consegnato|entregado|bezorgd)\b", re.I)),
    ("delayed", re.compile(r"^(delivery estimate update|lieferdatum|aggiornamento)", re.I)),
]
RETAIL_KIND = [
    ("cancelled", re.compile(r"cancel+ed your order|order (has been )?cancel+ed|we('|’)ve cancel+ed", re.I)),
    ("delivered", re.compile(r"ready to collect|has been delivered|was delivered|we('|’)ve delivered|delivered today", re.I)),
    ("out", re.compile(r"out for delivery|will be delivered today|on its way today", re.I)),
    ("shipped", re.compile(r"on (their|its) way|dispatched|has shipped|has been sent|despatched", re.I)),
    ("ordered", re.compile(r"confirm(ation)? (of )?(your )?.*order|order confirm|thanks for your order|order received|we('|’)ve got your order", re.I)),
]
IGNORE = re.compile(r"payment declined|review|rate your|did .* meet|perks|offer|deal|sale|% off|newsletter|members|subscription|"
                    r"guarantee|refund|receipt for safekeeping|ticket \[#|feedback|unused prime|enquiry|question", re.I)
ORDER_RE = re.compile(r"(?:order\s*#|bestellnr\.?|commande n°|ordine n\.|pedido n\.?º?|order(?: number)?:?)\s*[‫‎#]*\s*(\d{3}-\d{7}-\d{7}|CUR\d{6,}|\d{8,12})", re.I)
AMZ_ORDER = re.compile(r"\b(\d{3}-\d{7}-\d{7})\b")


def _site(sender):
    m = re.search(r"amazon\.(co\.uk|de|fr|it|es|nl|com)", sender)
    if m:
        return "Amazon " + {"co.uk": "UK", "com": "US"}.get(m.group(1), m.group(1).upper())
    dom = sender.split("@")[-1]
    for name in ("currys", "johnlewis", "costco", "argos", "diy.com", "tradepoint", "very", "ebuyer", "game", "boots",
                 "superdrug", "lookfantastic", "harveynorman", "sportsdirect", "toolstation", "screwfix", "awd-it",
                 "a1techdeals", "approvedfood", "lloydspharmacy", "dpd"):
        if name in dom:
            return {"johnlewis": "John Lewis", "diy.com": "B&Q", "tradepoint": "TradePoint", "game": "GAME", "dpd": "DPD",
                    "awd-it": "AWD-IT", "harveynorman": "Harvey Norman", "sportsdirect": "Sports Direct",
                    "lookfantastic": "Lookfantastic", "a1techdeals": "A1Techdeals", "approvedfood": "ApprovedFood",
                    "lloydspharmacy": "Lloydspharmacy"}.get(name, name.title())
    return dom


def _order_link(site, order):
    if not (site.startswith("Amazon") and order):
        return None
    tld = {"Amazon UK": "co.uk", "Amazon US": "com"}.get(site, site[7:].lower())
    return f"https://www.amazon.{tld}/gp/your-account/order-details?orderID={order}"


def _received(msg):
    try:
        d = email.utils.parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc)
        return (d + uk_offset(d)).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def _parse(msg, sender, subject):
    """One email -> one event dict (or None)."""
    site = _site(sender)
    amazon = site.startswith("Amazon")
    if amazon:
        kind = next((k for k, p in AMZ_KIND if p.search(subject)), None)
    else:
        kind = next((k for k, p in RETAIL_KIND if p.search(subject)), None)
    if not kind:
        return None
    text = otp_watch._text_nodes(msg)
    text = re.sub(r"[‪-‮‎‏]", "", text)
    order = (AMZ_ORDER.search(subject) or AMZ_ORDER.search(text)) if amazon else (ORDER_RE.search(subject) or ORDER_RE.search(text))
    order = order.group(1) if order else None
    # first item: subject has qty + truncated title; the body has "Quantity: N" / "Menge: N"
    sm = (re.search(r":\s*(?:(\d+)\s+)?[‘„“«]\s*(.+?)(?:\.\.\.|…)?[’“”»]\s*(?:and (\d+) more items?|und (\d+) weitere)?", subject)
          or re.search(r":\s*(?:(\d+)\s+)?[\"']\s*(.+?)(?:\.\.\.|…)?[\"']\s*(?:and (\d+) more items?|und (\d+) weitere)?\s*$", subject))
    title = sm.group(2).strip() if sm else None
    qty = int(sm.group(1)) if sm and sm.group(1) else None
    more = int(sm.group(3) or sm.group(4) or 0) if sm else 0
    if qty is None:
        q = re.search(r"(?:Quantity|Menge|Quantité|Quantità|Cantidad):\s*(\d+)", text)
        qty = int(q.group(1)) if q else (int(re.search(r"\b(\d+)x\s", text).group(1)) if re.search(r"\b(\d+)x\s", text) else 1)
    if not title and amazon:
        bm = re.search(r"(?:View or edit order|Track package|Bestellung ansehen oder ändern|Lieferung verfolgen|View order details)\s+(.{6,90}?)\s+(?:Sold by|Verkauf durch|Vendu par|Venduto da|Vendido por|Quantity|Menge|Condition|Zustand)", text)
        title = bm.group(1).strip(" .*") if bm else None
    if not title and not amazon:
        cm = re.search(r"\b\d+x\s+(.{6,80}?)\s+(?:Product code|£)", text)
        title = cm.group(1).strip() if cm else None
    tot = re.search(r"(?:Total|Summe|Totale|Order total)\s*[:]?\s*([£€$])?\s*([\d.,]+)\s*([£€])?", text)
    total, cur = None, None
    if tot:
        try:
            total = float(tot.group(2).replace(",", "")) if tot.group(2).count(".") <= 1 else None
            cur = tot.group(1) or tot.group(3) or ("€" if site in ("Amazon DE", "Amazon FR", "Amazon IT", "Amazon ES", "Amazon NL") else "£")
        except ValueError:
            pass
    dest = next((name for name, pat in otp_watch.DESTINATIONS if pat.search(text)), None)
    eta = re.search(r"(?:Now Arriving|Arriving|Zustellung:|Livraison|Arrivo|Llegada)\s*:?\s*([A-Za-zäéèû]+(?:,? \d{1,2}\.? [A-Za-zäéèû]+(?: \d{4})?)?|\d{1,2}\.? [A-Za-zäéèû]+)", text)
    return {"kind": kind, "site": site, "order": order, "title": title, "qty": qty, "moreItems": more,
            "total": total, "currency": cur, "dest": dest, "eta": eta.group(1) if eta and kind in ("ordered", "shipped", "delayed") else None,
            "subject": subject[:200]}


def scan_mail():
    """Parse order emails from the last DAYS days. Bodies are fetched once and cached by Message-ID."""
    try:
        cache = json.loads(MAIL_CACHE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    since = (datetime.now() - timedelta(days=DAYS + 2)).strftime("%d-%b-%Y")
    errors, seen = [], {}
    for addr, pw, host in important.imap_accounts():
        if "paste" in pw:
            continue
        try:
            M = imaplib.IMAP4_SSL(host, 993, timeout=60)
            M.login(addr, pw)
            M.select('"[Gmail]/All Mail"' if "gmail" in host else "INBOX", readonly=True)
            ids = set()
            for term in SENDER_TERMS:
                typ, d = M.search(None, f'(SINCE "{since}" FROM "{term}")')
                if typ == "OK":
                    ids.update((d[0] or b"").split())
            ids = sorted(ids, key=int)
            heads = {}
            for k in range(0, len(ids), 300):
                typ, data = M.fetch(b",".join(ids[k:k + 300]).decode(), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID DATE)])")
                num = None
                for part in data:
                    if isinstance(part, tuple):
                        num = part[0].split()[0]
                        heads[num] = email.message_from_bytes(part[1])
            need = []
            for num, h in heads.items():
                mid = (h.get("Message-ID") or f"{addr}-{num.decode()}").strip()
                sender = email.utils.parseaddr(important._dec(h.get("From")))[1].lower()
                subj = important._dec(h.get("Subject")).strip()
                if mid in seen or IGNORE.search(subj):
                    continue
                kinds = AMZ_KIND if "amazon." in sender else RETAIL_KIND
                if not any(p.search(subj) for _, p in kinds):
                    continue
                seen[mid] = True
                if mid not in cache:
                    need.append((num, mid, sender, subj))
            for k in range(0, len(need), 40):
                chunk = need[k:k + 40]
                typ, data = M.fetch(b",".join(n for n, *_ in chunk).decode(), "(BODY.PEEK[])")
                bodies = {}
                for part in data:
                    if isinstance(part, tuple):
                        bodies[part[0].split()[0]] = part[1]
                for num, mid, sender, subj in chunk:
                    if num not in bodies:
                        continue
                    msg = email.message_from_bytes(bodies[num])
                    ev = _parse(msg, sender, subj)
                    cache[mid] = {"at": _received(msg).isoformat(timespec="minutes"), "account": addr, **(ev or {"kind": None})}
            M.logout()
        except Exception as e:
            errors.append(f"{addr}: {e}")
    cutoff = (datetime.now() - timedelta(days=DAYS + 5)).isoformat()
    cache = {k: v for k, v in cache.items() if v.get("at", "") >= cutoff}
    MAIL_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return [v for k, v in cache.items() if k in seen and v.get("kind")], errors


def fetch_invenno():
    """Recent Invenno purchases with prep-centre and shipment data (through the shared profile lock)."""
    paths = {f"p{i}": f"/api/v1/purchases?page={i}&limit=50" for i in range(1, 13)}
    raw = invenno.browser_get(paths)
    out, ids = [], set()
    cutoff = (datetime.now() - timedelta(days=DAYS + 15)).date().isoformat()
    for k in sorted(raw, key=lambda x: int(x[1:])):
        for p in raw[k]["data"]["purchases"]:
            if p["id"] in ids or p["purchaseDate"][:10] < cutoff:
                continue
            ids.add(p["id"])
            pr, pc = p.get("product") or {}, p.get("prepCenterParcel") or {}
            inv = (pr.get("amazonInventory") or pr.get("AmazonInventory") or [{}])
            out.append({
                "id": p["id"], "date": p["purchaseDate"][:10], "asin": p.get("asin"), "title": pr.get("title") or p.get("name") or "",
                "image": pr.get("imageUrl"), "brand": pr.get("brand"), "qty": p.get("orderedQuantity") or p.get("asinQuantity") or 0,
                "unit": round((p.get("purchasePrice") or 0) / 100, 2), "a2a": pc.get("orderType") == "Amazon to Amazon",
                "delivered": bool(p.get("isDelivered")), "deliveredQty": p.get("deliveredQuantity") or 0,
                "prepStatus": pc.get("status"), "received": pc.get("unitsReceived") or 0, "prepped": pc.get("unitsPrepped") or 0,
                "missing": bool(pc.get("unitsMissing")), "leftToPrep": pc.get("unitsLeftToPrep"), "prepDelivered": pc.get("dateDelivered"),
                "prepUpdated": (pc.get("updatedAt") or "")[:10] or None,
                "sent": sum(a.get("allocatedQuantity") or 0 for a in (p.get("shipmentAllocations") or []) if a.get("status") == "ACTIVE"),
                "live": sum((i or {}).get("fulfillableQuantity") or 0 for i in inv),
            })
    return out


_STOP = {"the", "and", "with", "for", "von", "mit", "und", "pour", "per", "con", "de", "la", "le", "les", "der", "die", "das", "set", "pack"}


def _norm(s):
    import unicodedata
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


def _tokens(s):
    return [w for w in re.findall(r"[a-z0-9]+", _norm(s).replace("kompakt", "compact")) if len(w) > 2 and w not in _STOP][:7]


def _models(s):
    """Model-number-like tokens (letters + digits), strong evidence across languages: BHH880, 41432, 05006618001."""
    return {w for w in re.findall(r"[a-z0-9]+", _norm(s)) if len(w) >= 4 and re.search(r"\d", w) and re.search(r"[a-z]", w) or (w.isdigit() and len(w) >= 5)}


def _match(line, purchases):
    lt = set(_tokens(line["title"]))
    if not lt:
        return None
    best, score = None, 0
    od = line["orderedAt"][:10]
    for p in purchases:
        dd = (datetime.fromisoformat(p["date"]) - datetime.fromisoformat(od)).days
        if dd < -2 or dd > 6:
            continue
        pt = set(_tokens(p["title"]))
        if not pt:
            continue
        s = len(lt & pt) / len(lt)
        if _models(line["title"]) & _models(p["title"]):
            s += .5
        if p["qty"] == line["qty"]:
            s += .15
        s -= abs(dd) * .02
        if s > score:
            best, score = p, s
    return best if score >= .5 else None


def build():
    if not important.imap_accounts():
        return {"configured": False}
    events, errors = scan_mail()
    try:
        inv = fetch_invenno()
    except invenno.NeedsLogin:
        inv, errors = [], errors + ["Invenno login expired: prep-centre stages unavailable until you log in (connect-invenno.bat)."]
    except Exception as e:
        inv, errors = [], errors + [f"Invenno purchases: {e}"]

    # Group email events into order lines (order number + first item)
    lines = {}
    for ev in sorted(events, key=lambda e: e["at"]):
        key = ev.get("order") or f"{ev['site']}|{(ev.get('title') or '')[:25].lower()}"
        ln = lines.get(key)
        if not ln:
            if ev["kind"] not in ("ordered",) and not ev.get("order"):
                continue  # stray dispatch/delivery with nothing to attach to
            ln = lines[key] = {"key": key, "order": ev.get("order"), "site": ev["site"], "title": ev.get("title") or "",
                               "qty": ev.get("qty") or 1, "moreItems": ev.get("moreItems") or 0, "total": ev.get("total"),
                               "currency": ev.get("currency"), "dest": ev.get("dest"), "orderedAt": ev["at"], "events": {}, "eta": None}
        if ev["kind"] == "ordered":
            ln["orderedAt"] = min(ln["orderedAt"], ev["at"])
            ln["pendingPayment"] = "pending verification" in ev.get("subject", "").lower()
        ln["events"].setdefault(ev["kind"], ev["at"])
        for f in ("title", "dest", "total", "currency"):
            if not ln.get(f) and ev.get(f):
                ln[f] = ev[f]
        if ev.get("eta"):
            ln["eta"] = ev["eta"]

    cutoff = (datetime.now() - timedelta(days=DAYS)).isoformat()
    now = datetime.now()
    used = set()
    cards = []

    def stage_of(c, p):
        if c.get("cancelled"):
            return "cancelled"
        if p:
            if p["live"] > 0 and p["sent"] > 0:
                return "live"
            if p["sent"] > 0:
                return "sent"
            if p["prepStatus"] == "Complete" or (p["qty"] and p["prepped"] >= p["qty"]):
                return "prepped"
            if p["received"] > 0 or p["prepStatus"] in ("Received", "In Progress", "Needs Attention", "Partially Received", "In Warehouse"):
                return "atprep"
        ev = c.get("events", {})
        if "delivered" in ev or (p and p["delivered"]):
            return "delivered"
        if "shipped" in ev or "out" in ev:
            return "shipped"
        return "ordered"

    for ln in lines.values():
        if ln["orderedAt"] < cutoff and "delivered" in ln["events"]:
            continue
        p = _match(ln, inv)
        if p:
            used.add(p["id"])
        c = {"id": ln["key"], "source": ln["site"], "order": ln["order"], "title": ln["title"], "qty": ln["qty"],
             "moreItems": ln["moreItems"], "total": ln["total"], "currency": ln["currency"], "dest": ln["dest"],
             "orderedAt": ln["orderedAt"], "events": ln["events"], "eta": ln["eta"], "pendingPayment": ln.get("pendingPayment"),
             "cancelled": "cancelled" in ln["events"], "inv": p,
             "link": _order_link(ln["site"], ln["order"])}
        cards.append(c)
    for p in inv:  # purchases in Invenno with no order email (other accounts, in-store, not yet connected inboxes)
        if p["id"] in used or (p["date"] < cutoff[:10] and (p["sent"] > 0 or not p["prepStatus"])):
            continue
        cards.append({"id": f"inv-{p['id']}", "source": "Invenno", "order": None, "title": p["title"], "qty": p["qty"],
                      "total": round(p["unit"] * p["qty"], 2), "currency": "£", "dest": "Prep" if p["prepStatus"] else None,
                      "orderedAt": p["date"] + "T00:00", "events": {}, "eta": None, "cancelled": False, "inv": p, "link": None})

    for c in cards:
        p = c["inv"]
        c["stage"] = stage_of(c, p)
        if c["title"] == "" and p:
            c["title"] = p["title"]
        if p and p.get("image"):
            c["image"] = p["image"]
        probs = []
        age = (now - datetime.fromisoformat(c["orderedAt"])).days
        ev = c["events"]
        eu = c["source"] in ("Amazon DE", "Amazon FR", "Amazon IT", "Amazon ES", "Amazon NL")
        if c["cancelled"]:
            probs.append({"type": "cancelled", "text": "Order cancelled" + (" (payment)" if c.get("pendingPayment") else "")})
        if p and (p["missing"] or p["prepStatus"] == "Needs Attention"):
            probs.append({"type": "missing", "text": "Prep: " + ("units missing" if p["missing"] else "needs attention") +
                          f" ({p['received']}/{p['qty']} received)"})
        if c["source"] == "Invenno":
            # No order email in the connected inboxes: we only know what the prep centre knows
            eu = bool(p and p.get("a2a"))
            if p and p["prepStatus"] == "In Transit" and c["stage"] == "ordered":
                c["stage"] = "shipped"
                c["note"] = "Prep centre is expecting it"
                lim = STUCK["eu_delivery"] if eu else STUCK["uk_delivery"]
                if age > lim:
                    probs.append({"type": "stuck", "text": f"Not received at prep after {age} days"})
            elif c["stage"] == "ordered":
                c["note"] = "No order email in connected inboxes and not booked in at prep"
                c["untracked"] = True
        elif c["stage"] in ("ordered", "shipped") and not c["cancelled"]:
            lim = STUCK["eu_delivery"] if eu else STUCK["uk_delivery"]
            if age > lim:
                probs.append({"type": "stuck", "text": f"Not delivered after {age} days"})
        dl = ev.get("delivered") or (p and p.get("prepDelivered"))
        if c["stage"] in ("delivered", "atprep") and c.get("dest") != "Me" and dl:
            d = (now - datetime.fromisoformat(dl[:16])).days
            if d > STUCK["prep"]:
                probs.append({"type": "stuck", "text": f"Delivered {d} days ago, not prepped yet"})
        if c["stage"] == "prepped" and p and p.get("prepUpdated"):
            d = (now - datetime.fromisoformat(p["prepUpdated"])).days
            if d > STUCK["send_in"]:
                probs.append({"type": "stuck", "text": f"Prepped {d} days ago, not sent to Amazon"})
        if not c["title"]:
            c["title"] = f"{c['source']} order {c.get('order') or ''}".strip()
        if not p and c["source"] != "Invenno" and not c["cancelled"] and age >= 2:
            probs.append({"type": "notinvenno", "text": "Not found in Invenno purchases"})
        if "delayed" in ev and c["stage"] in ("ordered", "shipped"):
            c["delayed"] = True
        c["problems"] = probs

    notes = load_notes()
    for c in cards:
        n = notes.get(c["id"])
        c["userNote"] = n["text"] if n else ""
        c["userNoteAt"] = n["at"] if n else ""
    order = ["ordered", "shipped", "delivered", "atprep", "prepped", "sent", "live", "cancelled"]
    cards.sort(key=lambda c: (order.index(c["stage"]), c["orderedAt"]), reverse=False)
    recent = [c for c in cards if c["orderedAt"] >= cutoff]
    summary = {
        "orders": len([c for c in recent if c["source"] != "Invenno"]),
        "units": sum(c["qty"] or 0 for c in recent if not c["cancelled"]),
        "spendGBP": round(sum(p["unit"] * p["qty"] for p in inv if p["date"] >= cutoff[:10]), 2),
        "unitsReceived": sum(p["received"] for p in inv if p["date"] >= cutoff[:10]),
        "unitsPrepped": sum(p["prepped"] for p in inv if p["date"] >= cutoff[:10]),
        "unitsSent": sum(p["sent"] for p in inv if p["date"] >= cutoff[:10]),
        "missing": sum(1 for c in cards if any(x["type"] == "missing" for x in c["problems"])),
        "cancelled": sum(1 for c in recent if c["cancelled"]),
        "problems": sum(1 for c in cards if c["problems"]),
        "byStage": {s: sum(1 for c in cards if c["stage"] == s) for s in order},
    }
    try:
        import bank, ledger
        ledger.match_purchases(cards, bank.ledger_transactions()[0])
        for c in cards:
            for pr in c.get("problems", []):
                if pr["text"] == "No card payment found for this order":
                    pr["text"] = "No payment found on the connected cards"
    except Exception as e:
        errors.append(f"Bank matching: {e}")
    posted = alert(cards)
    try:
        sheet = sync_sheet(cards)
    except Exception as e:
        sheet, errors = None, errors + [f"Google Sheet sync failed: {e}"]
    return {"sheet": sheet, "configured": True, "updated": datetime.now().strftime("%H:%M"), "errors": errors, "summary": summary,
            "cards": cards, "posted": posted, "accounts": [a for a, _, _ in important.imap_accounts()],
            "limits": STUCK, "days": DAYS}


def load_notes():
    try:
        return json.loads(NOTES.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_note(key, text, at=None):
    notes = load_notes()
    at = at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    text = (text or "").strip()[:2000]
    old = notes.get(key)

    def ts(x):
        try:
            return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
    if old and ts(old.get("at")) > ts(at):
        return old  # a newer edit already exists
    notes[key] = {"text": text, "at": at}
    NOTES.write_text(json.dumps(notes, indent=1, ensure_ascii=False), encoding="utf-8")
    return notes[key]


STAGE_NAMES = {"ordered": "Ordered", "shipped": "In transit", "delivered": "Delivered", "atprep": "At prep",
               "prepped": "Prepped", "sent": "Sent to Amazon", "live": "Live", "cancelled": "Cancelled"}


def sync_sheet(cards):
    """Upsert every order into the user's 'Purchases Tracker' Google Sheet via its Apps Script web app.
    The script never deletes rows, so history is kept; it sorts oldest first."""
    env = load_env()
    url, token = env.get("SHEET_WEBHOOK_URL", ""), env.get("SHEET_WEBHOOK_TOKEN", "")
    if not url.startswith("https://script.google.com/") or not token:
        return None
    dest = {"Prep": f"Prep ({otp_watch.PREP_TOWN})", "Me": f"Home ({otp_watch.HOME_TOWN})"}
    rows = []
    for c in cards:
        p, ev = c.get("inv") or {}, c.get("events") or {}
        rows.append({
            "Key": c["id"], "Ordered": c["orderedAt"].replace("T", " "), "Store": c["source"], "Order number": c.get("order") or "",
            "Item": c.get("title") or "", "Qty": c.get("qty") or "", "Total": c.get("total") if c.get("total") is not None else "",
            "Currency": c.get("currency") or "", "Deliver to": dest.get(c.get("dest"), "Unknown"), "Stage": STAGE_NAMES.get(c["stage"], c["stage"]),
            "Shipped": (ev.get("shipped") or ev.get("out") or "").replace("T", " "), "Delivered": (ev.get("delivered") or "").replace("T", " "),
            "Received at prep": p.get("received", ""), "Prepped": p.get("prepped", ""), "Sent to Amazon": p.get("sent", ""), "Live": p.get("live", ""),
            "Problems": "; ".join(x["text"] for x in c.get("problems") or []), "Expected": (c.get("eta") or "") if c["stage"] in ("ordered", "shipped") else "",
            "Notes": c.get("userNote") or "", "NotesAt": c.get("userNoteAt") or "",
            "Payment": (f"£{c['payment']['amount']:.2f} · {c['payment']['source']} · {c['payment']['date']}" if c.get("payment") else ""),
            "Last updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    txrows = []
    try:
        import bank, ledger
        import copy
        L = ledger.build({"transactions": bank.ledger_transactions()[0]}, copy.deepcopy(cards))
        ans = ledger.load_answers()["txn"]
        for t in L["transactions"]:
            txrows.append({"Key": t["id"], "Date": t["date"], "Card / account": t["source"], "Merchant": t.get("merchant") or "",
                           "Description": t.get("description") or "", "Amount": t["amount"], "Original": (f"{t['origAmount']:.2f} {t['origCurrency']}" if t.get("origCurrency") not in (None, "", "GBP") else ""),
                           "Category": t.get("cat") or "", "How": {"you": "Your answer", "learned": "Learned from you", "rule": "Auto", "matched": "Matched order"}.get(t.get("catHow"), ""),
                           "Matched order": t.get("order") or t.get("note") or "", "Question": t.get("question") or "", "Answered": ans.get(t["id"], "")})
    except Exception:
        txrows = []
    req = urllib.request.Request(url, data=json.dumps({"token": token, "rows": rows, "transactions": txrows}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode() or "{}")
    # Notes typed in the sheet (newer than ours) come back here
    for key, n in (res.get("notes") or {}).items():
        set_note(key, n.get("text", ""), n.get("at"))
        for c in cards:
            if c["id"] == key:
                c["userNote"], c["userNoteAt"] = n.get("text", ""), n.get("at")
    # Categories you picked in the sheet's Transactions tab: remember them (and the merchant) for next time
    if res.get("answers"):
        import ledger
        keys = {r["Key"]: r for r in txrows}
        for key, cat in res["answers"].items():
            r = keys.get(key)
            if r and cat in ledger.CATEGORIES:
                ledger.answer(key, cat, ledger.merchant_key({"merchant": r["Merchant"], "description": r["Description"]}))
    return {k: v for k, v in res.items() if k not in ("notes", "answers")}


def alert(cards):
    """Post new problems to the user's #purchase-alerts Discord webhook (each problem once)."""
    url = load_env().get("PURCHASE_WEBHOOK_URL", "")
    if not url.startswith("https://discord.com/api/webhooks/"):
        return 0
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = None
    first = state is None
    state = state or {"posted": []}
    done = set(state["posted"])
    colours = {"cancelled": 0xFF6B81, "missing": 0xFFC857, "stuck": 0x8B7BFF, "notinvenno": 0x4FD1FF, "money": 0xFF8A50}
    icons = {"cancelled": "❌", "missing": "⚠️", "stuck": "⏳", "notinvenno": "❓", "money": "💳"}
    n = 0
    for c in cards:
        for pr in c["problems"]:
            key = f"{c['id']}|{pr['type']}|{pr['text'] if pr['type'] != 'stuck' else c['stage']}"
            if key in done:
                continue
            done.add(key)
            if first:
                continue  # first run: remember existing problems, don't flood the channel
            fields = [{"name": "Order", "value": f"{c['source']}" + (f" · {c['order']}" if c.get("order") else ""), "inline": True},
                      {"name": "Qty", "value": str(c.get("qty") or "?"), "inline": True},
                      {"name": "Stage", "value": c["stage"], "inline": True}]
            body = {"content": f"{icons[pr['type']]} **{pr['text']}**: {c['title'][:120]}",
                    "embeds": [{"color": colours[pr["type"]], "fields": fields, "url": c.get("link"), "title": c["title"][:250],
                                "footer": {"text": "Command Centre · purchases tracker"}}],
                    "allowed_mentions": {"parse": []}}
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                             headers={"Content-Type": "application/json", "User-Agent": "CommandCentre/1.0"})
                urllib.request.urlopen(req, timeout=20).read()
                n += 1
            except Exception:
                done.discard(key)
    state["posted"] = list(done)[-3000:]
    STATE.write_text(json.dumps(state), encoding="utf-8")
    return n


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: d[k] for k in ("summary", "errors")}, indent=1, ensure_ascii=False))
    for c in d["cards"][:40]:
        print(c["stage"], "|", c["source"], c.get("order"), "|", c["qty"], (c["title"] or "")[:50], "|", c.get("dest"),
              "| inv" if c["inv"] else "| -", [p["text"] for p in c["problems"]])
