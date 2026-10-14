"""Insights page: refund & cancellation chaser, Monday money digest, cash-flow estimate, stock ageing.
Everything is dashboard-only (the user chose no Discord for these)."""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
CHASE = ROOT / "chaser_state.json"
CHASE_DAYS = 7


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def chaser(cards):
    """Orders charged but cancelled, or with units missing at prep. Due once 7 days old, then again 7 days after each 'Chased'."""
    st = _load(CHASE, {})
    now = datetime.now()
    due, waiting = [], []
    for c in cards:
        probs = [p for p in c.get("problems", []) if p["type"] == "missing" or p["text"].startswith("Cancelled but charged")]
        if not probs:
            continue
        k = c["id"]
        start = (c.get("events") or {}).get("cancelled") or c.get("orderedAt") or now.isoformat(timespec="minutes")
        s = st.setdefault(k, {"firstSeen": start[:16]})
        if s["firstSeen"] > start[:16]:
            s["firstSeen"] = start[:16]   # count from when the problem started, not when the tracker first saw it
        if s.get("resolved"):
            continue
        since = datetime.fromisoformat(s.get("lastChased") or s["firstSeen"])
        days = (now - since).days
        item = {"key": k, "source": c["source"], "order": c.get("order"), "title": c.get("title"), "qty": c.get("qty"),
                "total": c.get("total"), "currency": c.get("currency"), "link": c.get("link"), "problems": [p["text"] for p in probs],
                "firstSeen": s["firstSeen"][:10], "lastChased": (s.get("lastChased") or "")[:10], "chasedTimes": s.get("times", 0),
                "daysWaiting": (now - datetime.fromisoformat(s["firstSeen"])).days, "dueIn": max(0, CHASE_DAYS - days)}
        (due if days >= CHASE_DAYS else waiting).append(item)
    CHASE.write_text(json.dumps(st, indent=1), encoding="utf-8")
    return {"due": due, "waiting": sorted(waiting, key=lambda x: x["dueIn"]), "days": CHASE_DAYS}


def chase_action(key, action):
    st = _load(CHASE, {})
    s = st.setdefault(key, {"firstSeen": datetime.now().isoformat(timespec="minutes")})
    if action == "chased":
        s["lastChased"] = datetime.now().isoformat(timespec="minutes")
        s["times"] = s.get("times", 0) + 1
    elif action == "resolved":
        s["resolved"] = datetime.now().isoformat(timespec="minutes")
    elif action == "reopen":
        s.pop("resolved", None)
    CHASE.write_text(json.dumps(st, indent=1), encoding="utf-8")
    return s


def digest(cards, ledger_data, fba, chase):
    """Last full week (Mon-Sun)."""
    today = date.today()
    mon = today - timedelta(days=today.weekday() + 7)
    sun = mon + timedelta(days=6)
    inweek = lambda d: d and mon.isoformat() <= d[:10] <= sun.isoformat()
    tx = [t for t in ledger_data.get("transactions", []) if inweek(t["date"]) and t["amount"] < 0 and t.get("cat") != "Transfers"]
    by_cat = {}
    for t in tx:
        by_cat[t.get("cat") or "Uncategorised"] = round(by_cat.get(t.get("cat") or "Uncategorised", 0) + abs(t["amount"]), 2)
    bought = [c for c in cards if inweek(c.get("orderedAt")) and not c.get("cancelled")]
    sales = profit = None
    dates = fba.get("dates") or []
    if dates and fba.get("sales30"):
        sales = round(sum(v for d, v in zip(dates, fba["sales30"]) if inweek(d)), 2)
        profit = round(sum(v for d, v in zip(dates, fba.get("profit30") or []) if inweek(d)), 2)
    stuck = [c for c in cards if any(p["type"] == "stuck" for p in c.get("problems", []))]
    return {"from": mon.isoformat(), "to": sun.isoformat(), "spend": round(sum(abs(t["amount"]) for t in tx), 2),
            "spendByCategory": dict(sorted(by_cat.items(), key=lambda x: -x[1])),
            "ordersPlaced": len(bought), "unitsBought": sum(c.get("qty") or 0 for c in bought),
            "stockSpend": round(sum(float(c.get("total") or 0) for c in bought if (c.get("currency") or "£") == "£"), 2),
            "sales": sales, "profit": profit, "questions": len(ledger_data.get("questions", [])),
            "refundsOutstanding": len(chase["due"]) + len(chase["waiting"]), "stuck": len(stuck)}


def cashflow(ledger_data, raw_txns, fba):
    """Estimate from the statements: what's owed on the cards since their last repayment, cash in Revolut, weekly burn."""
    tx = raw_txns
    cards = {}
    for prov in ("Amex (CSV)", "Capital on Tap (CSV)"):
        rows = sorted([t for t in tx if t.get("provider") == prov], key=lambda t: t["date"])
        if not rows:
            continue
        pays = [t for t in rows if t["amount"] > 0 and any(w in (t.get("description") or "").lower() for w in ("payment received", "payment made", "thank you"))]
        last = pays[-1] if pays else None
        since = [t for t in rows if (not last or t["date"] > last["date"]) and t is not last]
        owed = round(-sum(t["amount"] for t in since), 2)
        monthly = {}
        for p in pays:
            monthly[p["date"][:7]] = monthly.get(p["date"][:7], 0) + p["amount"]
        avg = round(sum(monthly.values()) / len(monthly), 2) if monthly else None
        cards[prov.split(" (")[0]] = {"owedSinceLastPayment": owed, "lastPayment": last and {"date": last["date"], "amount": last["amount"]},
                                       "avgMonthlyRepayment": avg, "statementTo": rows[-1]["date"]}
    rev = sorted([t for t in tx if t.get("provider") == "Revolut (CSV)" and t.get("balance") is not None], key=lambda t: t["date"])
    revolut = {"balance": rev[-1]["balance"], "asOf": rev[-1]["date"]} if rev else None
    cutoff = (date.today() - timedelta(days=28)).isoformat()
    burn = sum(-t["amount"] for t in ledger_data.get("transactions", []) if t["date"] >= cutoff and t["amount"] < 0 and t.get("cat") != "Transfers")
    sales30 = round(sum(fba.get("sales30") or []), 2) if fba.get("sales30") else None
    owed_total = round(sum(c["owedSinceLastPayment"] for c in cards.values()), 2)
    return {"cards": cards, "revolut": revolut, "owedTotal": owed_total, "weeklySpend": round(burn / 4, 2),
            "amazonSales30": sales30, "gap": round((revolut["balance"] if revolut else 0) - owed_total, 2),
            "note": "Estimated from your statement exports: card balance = charges since the last repayment on each export. Upload fresh exports for an up-to-date picture."}
