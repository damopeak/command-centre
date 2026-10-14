"""Command Centre - demo mode.

Serves the dashboard from ./app at http://127.0.0.1:8799 and answers every /api/* endpoint
with realistic but entirely FAKE data, generated relative to today's date so the charts look alive.

    python demo_server.py

No accounts, API keys, browser sessions or third-party packages are needed (standard library only).
Nothing here is real: products, companies, people, order numbers and amounts are all invented.
"""
import hashlib
import json
import math
import random
import sys
from datetime import date, datetime, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

HOST, PORT = "127.0.0.1", 8799
APP_DIR = Path(__file__).parent / "app"
STARTED = datetime.now() - timedelta(hours=6, minutes=12)


# ---------- helpers ----------
def now():
    return datetime.now()


def today():
    return date.today()


def iso(dt):
    return dt.isoformat(timespec="minutes")


def hm():
    return now().strftime("%H:%M")


def seeded(*parts):
    """A random generator that gives the same numbers for the same key (stable across reloads)."""
    h = hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()
    return random.Random(int(h[:12], 16))


def label(d):
    return f"{d.day} {d.strftime('%b')}"


# ---------- sales (Invenno-shaped) ----------
PRODUCTS = [
    ("DEMO0A1B2C", "Cordless Stick Vacuum, 2-in-1 Lightweight, Grey"),
    ("DEMO1D3E4F", "Electric Toothbrush Twin Pack with Travel Case"),
    ("DEMO2G5H6J", "Building Bricks Space Shuttle Set (1,200 pieces)"),
    ("DEMO3K7L8M", "Air Fryer 5.5L Digital, Black"),
    ("DEMO4N9P0Q", "Noise Cancelling Wireless Headphones, Midnight"),
    ("DEMO5R1S2T", "Smart Plug Mini 4-Pack, Wi-Fi"),
    ("DEMO6U3V4W", "Stainless Steel Insulated Bottle 750ml, Sage"),
    ("DEMO7X5Y6Z", "Hair Styler Multi-Attachment Set"),
    ("DEMO8A7B8C", "Family Board Game: Island Explorers"),
    ("DEMO9D9E0F", "LED Desk Lamp with Wireless Charger"),
    ("DEMOAG1H2J", "Robot Window Cleaner, Compact"),
    ("DEMOBK3L4M", "Kids' Smartwatch with Camera, Blue"),
]


def day_fraction():
    return max(0.15, min(1.0, (now().hour * 60 + now().minute) / 1260))


def day_figures(d, part_day=False):
    """Sales, profit, units and orders for one day: steady weekly rhythm plus noise."""
    r = seeded("sales", d.isoformat())
    weekly = 1.18 if d.weekday() >= 5 else 1.0
    trend = 1 + (d.toordinal() % 365) / 2400
    sales = (420 + 140 * math.sin(d.toordinal() / 4.3)) * weekly * trend * r.uniform(0.78, 1.25)
    if d == today() or part_day:
        sales *= day_fraction()  # today so far (and the same share of the comparison day)
    margin = r.uniform(0.17, 0.26)
    profit = sales * margin
    units = max(1, round(sales / r.uniform(24, 34)))
    return {"sales": round(sales, 2), "profit": round(profit, 2), "units": units, "orders": max(1, units - r.randint(0, 3)),
            "refunds": round(r.choice([0, 0, 0, 0, r.uniform(8, 40)]), 2)}


def totals(days, partial_last=False):
    rows = [day_figures(d, partial_last and i == len(days) - 1) for i, d in enumerate(days)]
    s = round(sum(x["sales"] for x in rows), 2)
    p = round(sum(x["profit"] for x in rows), 2)
    units = sum(x["units"] for x in rows)
    cost = s - p - s * 0.32  # rough marketplace fees so ROI looks believable
    return {"sales": s, "profit": p, "units": units, "orders": sum(x["orders"] for x in rows),
            "margin": round(p / s * 100, 2) if s else None, "roi": round(p / cost * 100, 2) if cost > 0 else None,
            "refunds": round(sum(x["refunds"] for x in rows), 2)}


def pct(a, b):
    return round((a - b) / abs(b) * 100, 1) if b else None


def top_products(days, n=10):
    span = len(days)
    out = []
    for i, (asin, title) in enumerate(PRODUCTS):
        r = seeded("top", asin, days[0].isoformat(), days[-1].isoformat())
        units = max(1, round(span * r.uniform(0.2, 1.1) * (1.6 - i * 0.1)))
        price = r.uniform(18, 140)
        sales = round(units * price, 2)
        margin = r.uniform(12, 30)
        profit = round(sales * margin / 100, 2)
        out.append({"asin": asin, "sku": f"DEMO-SKU-{i + 1:03d}", "title": title, "image": None, "units": units,
                    "sales": sales, "profit": profit, "roi": round(margin * 1.9), "margin": round(margin, 2)})
    out.sort(key=lambda x: -x["profit"])
    return out[:n]


def range_data(frm, to):
    to = min(to, today())
    if frm > to:
        frm = to
    days = [frm + timedelta(days=i) for i in range((to - frm).days + 1)]
    span = len(days)
    prev = [frm - timedelta(days=span - i) for i in range(span)]
    cur, pv = totals(days), totals(prev, partial_last=(to == today()))
    rows = [day_figures(d) for d in days]
    return {
        "from": str(frm), "to": str(to), "current": cur, "previous": pv,
        "change": {"profit": pct(cur["profit"], pv["profit"]), "sales": pct(cur["sales"], pv["sales"]), "units": pct(cur["units"], pv["units"])},
        "labels": [label(d) for d in days], "dates": [str(d) for d in days],
        "sales": [x["sales"] for x in rows], "profit": [x["profit"] for x in rows], "units": [x["units"] for x in rows],
        "topProducts": top_products(days),
    }


def fba():
    t = today()
    d30 = [t - timedelta(days=29 - i) for i in range(30)]
    month = [date(t.year, t.month, 1) + timedelta(days=i) for i in range(t.day)]
    prev_month_start = (date(t.year, t.month, 1) - timedelta(days=1)).replace(day=1)
    prev_month = [prev_month_start + timedelta(days=i) for i in range(t.day)]
    m, pm = totals(month), totals(prev_month)
    days_in_month = ((date(t.year + (t.month == 12), t.month % 12 + 1, 1)) - timedelta(days=1)).day
    rows = [day_figures(d) for d in d30]
    td, yd = totals([t]), totals([t - timedelta(days=1)])
    return {
        "configured": True, "source": "demo", "updated": hm(), "errors": [], "hasCosts": True,
        "today": {k: td[k] for k in ("sales", "profit", "units", "orders", "margin", "roi")},
        "yesterday": {k: yd[k] for k in ("sales", "profit", "units", "margin", "roi", "orders", "refunds")},
        "month": {**{k: m[k] for k in ("sales", "profit", "units", "margin", "roi")},
                  "profitChange": pct(m["profit"], pm["profit"]), "salesChange": pct(m["sales"], pm["sales"]),
                  "projectedProfit": round(m["profit"] / t.day * days_in_month, 2),
                  "projectedSales": round(m["sales"] / t.day * days_in_month, 2)},
        "d30": {k: v for k, v in totals(d30).items() if k != "orders"},
        "labels": [label(d) for d in d30], "dates": [str(d) for d in d30],
        "sales30": [x["sales"] for x in rows], "profit30": [x["profit"] for x in rows],
        "topProducts": top_products(d30),
        "alerts": [
            {"type": "amber", "title": "Air Fryer 5.5L Digital, Black", "meta": "About 9 days of stock left at current sales"},
            {"type": "amber", "title": "Smart Plug Mini 4-Pack, Wi-Fi", "meta": "Low stock: 4 units"},
            {"type": "red", "title": "Kids' Smartwatch with Camera, Blue", "meta": "Out of stock since yesterday"},
        ],
        "inventory": {"units": 486, "cost": 9184.4, "profit": 3210.75},
    }


# ---------- purchases ----------
def purchases():
    n = now()
    ago = lambda days, hours=0: iso(n - timedelta(days=days, hours=hours))
    inv = lambda qty, rec, prep, sent, live=0, status=None: {"qty": qty, "received": rec, "prepped": prep, "sent": sent, "live": live, "prepStatus": status}
    cards = [
        {"id": "demo-p01", "source": "Currys", "title": "Air Fryer 5.5L Digital, Black", "qty": 6, "stage": "ordered", "dest": "Prep",
         "total": 359.94, "currency": "£", "orderedAt": ago(0, 3), "eta": "Fri", "order": "DEMO-CU-48213", "problems": [], "pendingPayment": True},
        {"id": "demo-p02", "source": "Amazon DE", "title": "Noise Cancelling Wireless Headphones, Midnight", "qty": 4, "stage": "shipped", "dest": "Prep",
         "total": 596.0, "currency": "€", "orderedAt": ago(3), "eta": "Thu", "order": "DEMO-302-1184-55", "problems": [],
         "payment": {"amount": 517.32, "source": "Business credit card", "date": str(today() - timedelta(days=3))}},
        {"id": "demo-p03", "source": "Argos", "title": "Building Bricks Space Shuttle Set (1,200 pieces)", "qty": 3, "stage": "shipped", "dest": "Me",
         "total": 239.97, "currency": "£", "orderedAt": ago(2), "eta": "Tomorrow", "order": "DEMO-AR-90412", "problems": [], "delayed": True},
        {"id": "demo-p04", "source": "B&Q", "title": "Robot Window Cleaner, Compact", "qty": 2, "stage": "delivered", "dest": "Me",
         "total": 179.98, "currency": "£", "orderedAt": ago(5), "order": "DEMO-BQ-77310", "problems": [],
         "payment": {"amount": 179.98, "source": "Charge card", "date": str(today() - timedelta(days=5))}},
        {"id": "demo-p05", "source": "Amazon IT", "title": "Electric Toothbrush Twin Pack with Travel Case", "qty": 10, "stage": "atprep", "dest": "Prep",
         "total": 489.9, "currency": "€", "orderedAt": ago(9), "order": "DEMO-404-7731-90", "inv": inv(10, 8, 0, 0, status="Checked in"),
         "problems": [{"type": "missing", "text": "2 of 10 units not received at prep after 4 days"}]},
        {"id": "demo-p06", "source": "Currys", "title": "Hair Styler Multi-Attachment Set", "qty": 4, "stage": "atprep", "dest": "Prep",
         "total": 599.96, "currency": "£", "orderedAt": ago(7), "order": "DEMO-CU-47120", "inv": inv(4, 4, 0, 0, status="Queued for prep"), "problems": [],
         "payment": {"amount": 599.96, "source": "Business credit card", "date": str(today() - timedelta(days=7))}},
        {"id": "demo-p07", "source": "Amazon UK", "title": "Smart Plug Mini 4-Pack, Wi-Fi", "qty": 12, "stage": "prepped", "dest": "Prep",
         "total": 335.88, "currency": "£", "orderedAt": ago(12), "order": "DEMO-203-5521-08", "inv": inv(12, 12, 12, 0, status="Labelled"), "problems": [],
         "userNote": "Used 10% voucher code"},
        {"id": "demo-p08", "source": "Argos", "title": "Family Board Game: Island Explorers", "qty": 8, "stage": "sent", "dest": "Prep",
         "total": 159.92, "currency": "£", "orderedAt": ago(16), "order": "DEMO-AR-88104", "inv": inv(8, 8, 8, 8, status="Shipment created"), "problems": []},
        {"id": "demo-p09", "source": "Amazon DE", "title": "Stainless Steel Insulated Bottle 750ml, Sage", "qty": 20, "stage": "live", "dest": "Prep",
         "total": 279.8, "currency": "€", "orderedAt": ago(24), "order": "DEMO-302-6610-12", "inv": inv(20, 20, 20, 20, 17), "problems": []},
        {"id": "demo-p10", "source": "B&Q", "title": "LED Desk Lamp with Wireless Charger", "qty": 6, "stage": "live", "dest": "Prep",
         "total": 209.94, "currency": "£", "orderedAt": ago(27), "order": "DEMO-BQ-76002", "inv": inv(6, 6, 6, 6, 6), "problems": []},
        {"id": "demo-p11", "source": "Currys", "title": "Cordless Stick Vacuum, 2-in-1 Lightweight, Grey", "qty": 2, "stage": "cancelled", "dest": "Prep",
         "total": 298.0, "currency": "£", "orderedAt": ago(11), "order": "DEMO-CU-46655", "cancelled": True,
         "problems": [{"type": "cancelled", "text": "Order cancelled by the retailer"},
                      {"type": "money", "text": "Charged £298.00 but cancelled: no refund seen yet"}]},
        {"id": "demo-p12", "source": "Amazon IT", "title": "Kids' Smartwatch with Camera, Blue", "qty": 5, "stage": "delivered", "dest": "Prep",
         "total": 224.95, "currency": "€", "orderedAt": ago(23), "order": "DEMO-404-1209-33", "inv": inv(5, 0, 0, 0),
         "problems": [{"type": "stuck", "text": "Delivered 15 days ago but not checked in at prep"}]},
        {"id": "demo-p13", "source": "Argos", "title": "Cordless Stick Vacuum, 2-in-1 Lightweight, Grey", "qty": 3, "stage": "prepped", "dest": "Prep",
         "total": 447.0, "currency": "£", "orderedAt": ago(25), "order": "DEMO-AR-87010", "inv": inv(3, 3, 3, 0, status="Ready to ship"), "problems": []},
    ]
    for c in cards:
        c.setdefault("cancelled", False)
        c.setdefault("link", None)
    live = [c for c in cards if not c["cancelled"]]
    stages = ["ordered", "shipped", "delivered", "atprep", "prepped", "sent", "live", "cancelled"]
    summary = {
        "orders": len(cards), "units": sum(c["qty"] for c in live),
        "spendGBP": round(sum(c["total"] * (0.87 if c["currency"] == "€" else 1) for c in live), 2),
        "unitsReceived": sum((c.get("inv") or {}).get("received", 0) for c in live),
        "unitsPrepped": sum((c.get("inv") or {}).get("prepped", 0) for c in live),
        "unitsSent": sum((c.get("inv") or {}).get("sent", 0) for c in live),
        "missing": sum(1 for c in cards if any(p["type"] == "missing" for p in c["problems"])),
        "cancelled": sum(1 for c in cards if c["cancelled"]),
        "problems": sum(1 for c in cards if c["problems"]),
        "byStage": {s: sum(1 for c in cards if c["stage"] == s) for s in stages},
    }
    return {"sheet": None, "configured": True, "updated": hm(), "errors": [], "summary": summary, "cards": cards, "posted": 0,
            "accounts": ["orders@example.com"], "limits": {"eu_delivery": 10, "uk_delivery": 6, "prep": 5, "send_in": 7}, "days": 30}


# ---------- money (ledger) ----------
CATEGORIES = ["Stock", "Prep fees", "Shipping & postage", "Amazon fees", "Amazon payouts", "Refunds",
              "Software & subscriptions", "Phone & internet", "Accountant", "Bank fees",
              "Fuel", "Train", "Parking", "Meals", "Transfers", "Other / not sure"]


def money():
    r = seeded("money", today().isoformat())
    t0 = today()
    rows = []
    stock_merchants = ["CURRYS ONLINE", "ARGOS LTD", "AMAZON DE MARKETPLACE", "AMAZON IT MARKETPLACE", "B&Q ONLINE", "AMAZON UK RETAIL"]
    cards_src = ["Business credit card", "Charge card"]
    for i in range(18):
        m = stock_merchants[i % len(stock_merchants)]
        amt = -round(r.uniform(60, 620), 2)
        eur = "DE" in m or "IT" in m
        rows.append({"merchant": m.title().replace("Ltd", "Ltd"), "cat": "Stock", "catHow": "matched" if i % 3 else "rule", "amount": amt,
                     "days": r.randint(1, 85), "source": cards_src[i % 2], "order": f"Matched: DEMO order #{1000 + i * 7}" if i % 3 else "",
                     "origCurrency": "EUR" if eur else None, "origAmount": round(amt / 0.86, 2) if eur else None})
    fixed = [
        ("Prep Partner Ltd", "Prep fees", -184.5), ("Prep Partner Ltd", "Prep fees", -212.75), ("Prep Partner Ltd", "Prep fees", -96.0),
        ("Parcel Express", "Shipping & postage", -42.3), ("Parcel Express", "Shipping & postage", -18.9),
        ("Marketplace seller fees", "Amazon fees", -25.0), ("Marketplace payout", "Amazon payouts", 2840.12),
        ("Marketplace payout", "Amazon payouts", 3115.6), ("Currys refund", "Refunds", 149.0),
        ("Analytics Tool Pro", "Software & subscriptions", -39.0), ("Repricer Cloud", "Software & subscriptions", -59.0),
        ("Mobile Network Co", "Phone & internet", -22.0), ("Example Accountants", "Accountant", -95.0),
        ("Card account fee", "Bank fees", -7.5), ("Fuel Station", "Fuel", -61.2), ("Rail Tickets", "Train", -24.6),
        ("Card repayment", "Transfers", 1500.0), ("Card repayment", "Transfers", -1500.0),
    ]
    for j, (m, c, a) in enumerate(fixed):
        rows.append({"merchant": m, "cat": c, "catHow": "rule" if j % 2 else "learned", "amount": a, "days": r.randint(1, 88),
                     "source": "Business current account" if a > 0 else cards_src[j % 2], "order": ""})
    questions_src = [("Hardware Store 214", -48.99, "Card payment at a merchant I haven't seen before. Stock, or something else?"),
                     ("PAYPAL *DEMOSHOP", -132.4, "A PayPal payment with no matching order email. What was it for?"),
                     ("Cafe on the High St", -11.8, "Small card payment. Meals, or not business?")]
    for m, a, q in questions_src:
        rows.append({"merchant": m, "cat": None, "catHow": None, "amount": a, "days": r.randint(1, 12), "source": cards_src[0], "order": "", "question": q})
    txns, questions = [], []
    for k, x in enumerate(rows):
        d = t0 - timedelta(days=x["days"])
        mk = x["merchant"].lower().replace(" ", "-")
        t = {"id": f"demo-t{k:03d}", "date": str(d), "description": x["merchant"].upper(), "merchant": x["merchant"], "source": x["source"],
             "amount": x["amount"], "cat": x["cat"], "catHow": x["catHow"], "order": x.get("order") or "", "note": "",
             "origCurrency": x.get("origCurrency"), "origAmount": x.get("origAmount"), "merchantKey": mk}
        txns.append(t)
        if x.get("question"):
            questions.append({"id": t["id"], "date": t["date"], "merchant": t["merchant"], "description": t["description"], "source": t["source"],
                              "amount": t["amount"], "merchantKey": mk, "question": x["question"]})
    txns.sort(key=lambda t: t["date"], reverse=True)
    spend = {}
    for t in txns:
        if t["amount"] < 0:
            k = t["cat"] or "Uncategorised"
            spend[k] = round(spend.get(k, 0) + abs(t["amount"]), 2)
    return {"transactions": txns, "questions": questions, "spendByCategory": dict(sorted(spend.items(), key=lambda x: -x[1])),
            "spendByMonth": {}, "categories": CATEGORIES, "matched": sum(1 for t in txns if t["catHow"] == "matched"),
            "files": ["demo-card-export.csv", "demo-current-account.csv"], "sandbox": False, "connections": [], "testSources": 0}


# ---------- insights ----------
def insights():
    P = purchases()
    t0 = today()
    chaser = {
        "days": 7,
        "due": [
            {"key": "demo-p11", "source": "Currys", "qty": 2, "title": "Cordless Stick Vacuum, 2-in-1 Lightweight, Grey", "order": "DEMO-CU-46655",
             "problems": ["Charged £298.00 but cancelled: no refund seen yet"], "firstSeen": str(t0 - timedelta(days=10)),
             "chasedTimes": 0, "lastChased": None, "link": None, "dueIn": 0},
            {"key": "demo-p05", "source": "Amazon IT", "qty": 10, "title": "Electric Toothbrush Twin Pack with Travel Case", "order": "DEMO-404-7731-90",
             "problems": ["2 of 10 units not received at prep after 4 days"], "firstSeen": str(t0 - timedelta(days=8)),
             "chasedTimes": 1, "lastChased": str(t0 - timedelta(days=7)), "link": None, "dueIn": 0},
        ],
        "waiting": [
            {"key": "demo-x01", "source": "Argos", "qty": 1, "title": "Family Board Game: Island Explorers", "order": "DEMO-AR-88001",
             "problems": ["Return accepted: refund of £19.99 expected"], "firstSeen": str(t0 - timedelta(days=3)),
             "chasedTimes": 0, "lastChased": None, "link": None, "dueIn": 4},
        ],
    }
    mon = t0 - timedelta(days=t0.weekday() + 7)
    sun = mon + timedelta(days=6)
    wk = totals([mon + timedelta(days=i) for i in range(7)])
    digest = {"from": str(mon), "to": str(sun), "spend": 2314.6,
              "spendByCategory": {"Stock": 1876.4, "Prep fees": 212.75, "Software & subscriptions": 98.0, "Shipping & postage": 61.2, "Fuel": 66.25},
              "ordersPlaced": 7, "unitsBought": 41, "stockSpend": 1402.3, "sales": wk["sales"], "profit": wk["profit"],
              "questions": 3, "refundsOutstanding": 3, "stuck": 1}
    cashflow = {
        "cards": {
            "Business credit card": {"owedSinceLastPayment": 1842.37, "lastPayment": {"date": str(t0 - timedelta(days=19)), "amount": 2400.0},
                                     "avgMonthlyRepayment": 2650.0, "statementTo": str(t0 - timedelta(days=1))},
            "Charge card": {"owedSinceLastPayment": 936.12, "lastPayment": {"date": str(t0 - timedelta(days=12)), "amount": 1150.0},
                            "avgMonthlyRepayment": 1200.0, "statementTo": str(t0 - timedelta(days=2))},
        },
        "revolut": {"balance": 4127.55, "asOf": str(t0 - timedelta(days=1))},
        "owedTotal": 2778.49, "weeklySpend": 1984.3, "amazonSales30": round(sum(fba()["sales30"]), 2), "gap": round(4127.55 - 2778.49, 2),
        "note": "Demo figures. In the real app this is estimated from your statement exports: card balance = charges since the last repayment.",
    }
    srow = lambda i, stock, age, sold, cost: {"asin": PRODUCTS[i][0], "sku": f"DEMO-SKU-{i + 1:03d}", "title": PRODUCTS[i][1],
                                               "stock": stock, "age": age, "sold30": sold, "cost": cost, "tiedUp": round(stock * cost, 2)}
    no_sales = [srow(7, 6, 48, 0, 31.5), srow(11, 4, 39, 0, 27.0), srow(9, 3, 52, 0, 22.4)]
    old = [srow(7, 6, 48, 0, 31.5), srow(2, 5, 74, 2, 54.0), srow(4, 3, 66, 1, 71.2), srow(6, 14, 91, 4, 8.9)]
    stock = {"updated": now().strftime("%Y-%m-%d %H:%M"), "limits": {"notLive": 21, "noSales": 30, "old": 60},
             "noSales": no_sales, "old": old, "noSalesValue": round(sum(x["tiedUp"] for x in no_sales), 2),
             "oldValue": round(sum(x["tiedUp"] for x in old), 2), "stockValue": 9184.4}
    not_live = [{k: c.get(k) for k in ("source", "title", "qty", "stage", "orderedAt", "dest", "total", "currency")}
                for c in P["cards"] if not c["cancelled"] and c["stage"] in ("ordered", "shipped", "delivered", "atprep", "prepped")
                and (now() - datetime.fromisoformat(c["orderedAt"][:16])).days > 21]
    return {"chaser": chaser, "digest": digest, "cashflow": cashflow, "stock": stock, "notLive": not_live}


# ---------- important emails + delivery codes ----------
def important():
    n = now()
    gcal = lambda title, when: "https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + quote(title) + "&dates=" + when.strftime("%Y%m%dT%H%M00") + "/" + (when + timedelta(hours=1)).strftime("%Y%m%dT%H%M00")
    interview = (n + timedelta(days=2)).replace(hour=10, minute=30, second=0, microsecond=0)
    dentist = (n + timedelta(days=5)).replace(hour=15, minute=0, second=0, microsecond=0)
    items = [
        {"id": "demo-m1", "from": "Example Bank", "subject": "Unusual sign-in attempt on your business account", "category": "Security", "priority": 1,
         "reason": "Security alert", "unread": True, "received": iso(n - timedelta(minutes=48)),
         "snippet": "We noticed a sign-in from a new device. If this was you, no action is needed. If not, please secure your account now."},
        {"id": "demo-m2", "from": "Northwind Analytics Recruiting", "subject": "Interview invitation: Graduate Data Analyst", "category": "Job", "priority": 1,
         "reason": "Interview", "unread": True, "received": iso(n - timedelta(hours=3)),
         "snippet": "Thanks for applying. We'd like to invite you to a 45-minute video interview with the analytics team.",
         "eventDate": iso(interview), "eventTimed": True, "calendarUrl": gcal("Interview: Northwind Analytics", interview)},
        {"id": "demo-m3", "from": "Marketplace Seller Support", "subject": "Action needed: verify invoice for listing DEMO4N9P0Q", "category": "Business", "priority": 1,
         "reason": "Account health", "unread": False, "received": iso(n - timedelta(hours=9)),
         "snippet": "To keep this listing active, please upload a supplier invoice within 7 days."},
        {"id": "demo-m4", "from": "Courier Co", "subject": "We missed you: parcel held at your local depot", "category": "Life", "priority": 2,
         "reason": "Missed delivery", "unread": True, "received": iso(n - timedelta(hours=20)), "count": 2,
         "snippet": "Your parcel is being held for collection until Saturday. Bring photo ID and your collection code."},
        {"id": "demo-m5", "from": "Example Energy", "subject": "Your bill is ready: £84.20 due on the 28th", "category": "Money", "priority": 2,
         "reason": "Bill due", "unread": False, "received": iso(n - timedelta(days=1, hours=4)),
         "snippet": "Your latest statement is now available. The Direct Debit will be collected on the 28th."},
        {"id": "demo-m6", "from": "High Street Dental", "subject": "Appointment reminder", "category": "Life", "priority": 2,
         "reason": "Appointment", "unread": False, "received": iso(n - timedelta(days=1, hours=9)),
         "snippet": "This is a reminder of your check-up appointment. Reply C to confirm.",
         "eventDate": iso(dentist), "eventTimed": True, "calendarUrl": gcal("Dentist check-up", dentist)},
        {"id": "demo-m7", "from": "Sam (supplier)", "subject": "Re: pallet pricing for next month", "category": "People", "priority": 3,
         "reason": "Real person", "unread": False, "received": iso(n - timedelta(days=2, hours=2)),
         "snippet": "Hi, happy to hold last month's price if you can confirm the order by Friday. Cheers, Sam"},
        {"id": "demo-m8", "from": "Tax Office (demo)", "subject": "Your VAT return is due in 12 days", "category": "Money", "priority": 2,
         "reason": "Tax deadline", "unread": True, "received": iso(n - timedelta(days=3)),
         "snippet": "This is a reminder that your next VAT return and payment are due soon."},
    ]
    for x in items:
        x.setdefault("count", 1)
        x.update({"account": "demo@example.com", "to": "demo@example.com", "fromAddr": "noreply@example.com", "url": "https://mail.google.com/",
                  "groupKey": x["id"], "done": False})
    counts = {p: sum(1 for x in items if x["priority"] == p) for p in (1, 2, 3)}
    return {"configured": True, "updated": hm(), "errors": [], "accounts": ["demo@example.com", "orders@example.com"], "days": 7,
            "counts": counts, "unreadHigh": sum(1 for x in items if x["priority"] == 1 and x["unread"]), "items": items}


def otp():
    n = now()
    codes = [
        {"id": "demo-otp1", "code": "482913", "carrier": "Courier Co", "subject": "Your parcel arrives today: one-time code inside", "window": "today 10am - 2pm",
         "order": "DEMO-302-1184-55", "parcel": None, "item": "Noise Cancelling Wireless Headphones", "town": "Prep Town", "dest": "Prep",
         "to": "orders@example.com", "account": "orders@example.com", "received": iso(n - timedelta(hours=2)), "today": True, "posted": True},
        {"id": "demo-otp2", "code": "7351", "carrier": "Parcel Express", "subject": "Your delivery PIN", "window": "today 1pm - 2pm",
         "order": None, "parcel": "DEMO 4410 2277 91", "item": "Building Bricks Space Shuttle Set", "town": "Home Town", "dest": "Me",
         "to": "demo@example.com", "account": "demo@example.com", "received": iso(n - timedelta(minutes=35)), "today": True, "posted": True},
    ]
    return {"configured": True, "updated": hm(), "webhook": True, "errors": [], "postedNow": [], "codes": codes}


# ---------- calendar ----------
def calendar():
    t = datetime.combine(today(), datetime.min.time())
    ev = lambda d, h, m, mins, title, kind, cal, loc="": {
        "title": title, "start": iso(t + timedelta(days=d, hours=h, minutes=m)), "end": iso(t + timedelta(days=d, hours=h, minutes=m + mins)),
        "allDay": False, "location": loc, "calendar": cal, "kind": kind}
    allday = lambda d, title, kind, cal: {"title": title, "start": str(today() + timedelta(days=d)) + "T00:00", "end": str(today() + timedelta(days=d + 1)) + "T00:00",
                                         "allDay": True, "location": "", "calendar": cal, "kind": kind}
    events = [
        ev(0, 9, 0, 30, "Book inbound shipment with prep centre", "fba", "Business"),
        ev(0, 13, 0, 60, "Collect parcel from depot", "life", "Personal", "Courier Co depot"),
        ev(0, 16, 30, 45, "Supplier call: pallet pricing", "fba", "Business"),
        ev(1, 11, 0, 60, "Online assessment: Business Analyst (Lakeside Group)", "job", "Job hunt"),
        ev(2, 10, 30, 45, "Interview: Northwind Analytics", "job", "Job hunt", "Video call"),
        allday(3, "VAT return prep", "fba", "Business"),
        ev(4, 18, 0, 90, "Five-a-side football", "life", "Personal", "Leisure centre"),
        ev(5, 15, 0, 30, "Dentist check-up", "life", "Personal", "High Street Dental"),
        ev(6, 10, 0, 60, "Weekly stock review", "fba", "Business"),
        ev(8, 9, 30, 30, "Card repayment due", "fba", "Business"),
        ev(10, 14, 0, 60, "Assessment centre: Graduate SDR (Brightwave)", "job", "Job hunt", "Central London"),
        ev(12, 19, 0, 120, "Dinner with friends", "life", "Personal"),
    ]
    return {"configured": True, "updated": hm(), "errors": [], "calendars": ["Business", "Job hunt", "Personal"], "today": str(today()), "events": events}


# ---------- ISA ----------
FUNDS = [
    ("GLBL", "Global All Cap Index Fund (demo)", 38.2, 152.40, 0.23, 0.00031),
    ("USEQ", "US Equity Index Fund (demo)", 9.85, 612.10, 0.10, 0.00042),
    ("DEVX", "Developed World ex-UK Index Fund (demo)", 21.4, 498.75, 0.14, 0.00035),
    ("UKEQ", "UK Equity Index Fund (demo)", 14.6, 231.90, 0.06, 0.00012),
    ("EMKT", "Emerging Markets Index Fund (demo)", 31.0, 104.20, 0.22, 0.00018),
]
ISA_CASH = 142.37
ISA_NET = 16850.0


def isa():
    t0 = today()
    dates = [t0 - timedelta(days=i) for i in range(182, 0, -1)]
    dates = [d for d in dates if d.weekday() < 5]
    rows, series = [], [ISA_CASH] * len(dates)
    for k, (tic, name, units, price_now, ocf, drift) in enumerate(FUNDS):
        r = seeded("isa", tic, t0.isoformat())
        # walk backwards from today's price so the history ends where the live price is
        prices, p = [], price_now
        for _ in dates:
            prices.append(p)
            p = p / (1 + drift + r.gauss(0, 0.007))
        prices.reverse()
        prev = prices[-1]
        cost = units * price_now * r.uniform(0.84, 0.95)
        value = units * price_now
        for i, pp in enumerate(prices):
            series[i] += units * pp
        rows.append({"ticker": tic, "name": name, "units": units, "avgCost": round(cost / units, 2), "price": round(price_now, 4),
                     "value": round(value, 2), "cost": round(cost, 2), "gain": round(value - cost, 2),
                     "gainPct": round((value - cost) / cost * 100, 2), "day": round(units * (price_now - prev), 2),
                     "dayPct": round((price_now - prev) / prev * 100, 2), "ocf": ocf, "priced": "live" if k < 2 else "daily NAV"})
    total = sum(r["value"] for r in rows) + ISA_CASH
    invested = sum(r["cost"] for r in rows) + ISA_CASH
    day = sum(r["day"] for r in rows)
    for r in rows:
        r["weight"] = round(r["value"] / total * 100, 2)
    rows.sort(key=lambda r: -r["value"])
    series = [round(v, 2) for v in series] + [round(total, 2)]
    hdates = [str(d) for d in dates] + [str(t0)]
    w_ocf = sum(r["ocf"] * r["value"] for r in rows) / (total - ISA_CASH)
    return {"configured": True, "updated": hm(), "errors": [], "account": "Stocks & Shares ISA (demo)", "holdingsAsOf": str(t0 - timedelta(days=4)),
            "value": round(total, 2), "invested": round(invested, 2), "gain": round(total - invested, 2),
            "gainPct": round((total - invested) / invested * 100, 2), "day": round(day, 2), "dayPct": round(day / (total - day) * 100, 2),
            "netContributions": ISA_NET, "return": round(total - ISA_NET, 2), "cash": ISA_CASH, "ocf": round(w_ocf, 3),
            "annualFees": round(w_ocf / 100 * (total - ISA_CASH), 2), "holdings": rows, "historyDates": hdates, "history": series}


def isa_holdings():
    return {"account": "Stocks & Shares ISA (demo)", "asOf": str(today() - timedelta(days=4)), "cash": ISA_CASH, "netContributions": ISA_NET,
            "holdings": [{"ticker": t, "name": n, "units": u, "totalCost": round(u * p * 0.9, 2), "ocf": o} for t, n, u, p, o, _ in FUNDS]}


# ---------- deal monitors ----------
LEADS = [
    # title, source, buy, was, sell, hours ago, spm, store
    ("Cordless Stick Vacuum, 2-in-1 Lightweight, Grey", "DBH", 99.0, 149.0, 179.99, 1.5, 40, "Currys"),
    ("Air Fryer 5.5L Digital, Black", "Discord", 59.99, 79.99, 109.99, 3, 120, "Argos"),
    ("Building Bricks Space Shuttle Set (1,200 pieces)", "Currys", 64.99, 89.99, 104.0, 5, 65, "Currys"),
    ("Noise Cancelling Wireless Headphones, Midnight", "DBH", 129.0, 199.0, 189.0, 8, 30, "Amazon DE"),
    ("Electric Toothbrush Twin Pack with Travel Case", "Discord", 44.99, 69.99, 79.95, 22, 210, "B&Q"),
    ("Robot Window Cleaner, Compact", "Currys", 89.0, None, 139.0, 27, 18, "Currys"),
    ("Smart Plug Mini 4-Pack, Wi-Fi", "DBH", 24.0, 34.99, 39.99, 30, 300, "Argos"),
    ("Family Board Game: Island Explorers", "Discord", 17.5, 29.99, 32.99, 50, 90, "B&Q"),
    ("Hair Styler Multi-Attachment Set", "HUKD", 149.99, 199.99, None, 2, None, "Argos"),
    ("LED Desk Lamp with Wireless Charger", "HUKD", 27.99, 44.99, None, 6, None, "B&Q"),
]


def monitors():
    n = now()
    leads = []
    for i, (title, src, buy, was, sell, hrs, spm, store) in enumerate(LEADS):
        t = n - timedelta(hours=hrs)
        profit = round(sell * 0.85 - buy - 4.2, 2) if sell else None
        roi = round(profit / buy * 100) if profit is not None else None
        lead = {"title": title, "source": src, "monitor": src.lower(), "buy": buy, "was": was, "sell": sell, "profit": profit, "roi": roi,
                "store": store, "spm": spm, "tag": "Price drop" if was else "", "via": src, "time": iso(t),
                "url": "https://www.example.com/deals/demo-" + str(i), "supplierUrl": "https://www.example.com/shop/demo-" + str(i),
                "key": f"{src}|demo-{i}|{t.date()}"}
        if i == 0:
            lead["topPick"], lead["pickWhy"] = True, "Matches the brands you usually buy"
        if i == 7:
            lead["status"], lead["statusAt"] = "bought", iso(n - timedelta(hours=20))
        leads.append(lead)
    t0 = today()
    days = [t0 - timedelta(days=k) for k in range(6, -1, -1)]
    per_day = {}
    for st in ("HUKD", "DBH", "Currys", "Discord"):
        r = seeded("perday", st, t0.isoformat())
        base = {"HUKD": 9, "DBH": 3, "Currys": 2, "Discord": 4}[st]
        per_day[st] = [max(0, base + r.randint(-2, 3)) for _ in days]
    for l in leads:
        if l["time"][:10] == str(t0):
            per_day[l["source"]][-1] = max(per_day[l["source"]][-1], sum(1 for x in leads if x["source"] == l["source"] and x["time"][:10] == str(t0)))
    mon = lambda mid, name, store, desc, status, mins, event, med, best: {
        "id": mid, "name": name, "store": store, "desc": desc, "status": status, "running": status != "err", "canStart": status == "err",
        "lastActivity": iso(n - timedelta(minutes=mins)), "lastActivityMin": mins, "lastEvent": event, "warnings24h": 0,
        "leadsToday": per_day[store][-1], "leadsWeek": sum(per_day[store]), "medianRoi": med, "bestProfit": best,
        "lastLead": leads[0]["time"]}
    monitors_ = [
        mon("hukd", "HUKD Hot Deals", "HUKD", "Every 5 min · resale filter · posts to Discord", "ok", 2, "checked 40 hot deals, 1 new post", None, None),
        mon("dbh", "DBH new-lead notifier", "DBH", "Every 10 min · new deal → Discord embed", "ok", 6, "no new leads", 24, 41.8),
        mon("currys", "Currys price drops", "Currys", "Every 15 min · price drop + profit check", "ok", 11, "scanned 312 products, 2 drops", 19, 18.4),
        {**mon("discord", "Discord picks", "Discord", "On-demand checks of #deals-uk, #deals-eu (demo)", "ok", 140, "ask Claude: “check my Discord leads”", 31, 22.6),
         "manual": True, "running": True, "canStart": False},
    ]
    return {"configured": True, "updated": hm(), "errors": [], "monitors": monitors_, "leads": leads,
            "days": [d.strftime("%a") if d != t0 else "Today" for d in days], "perDay": per_day,
            "totals": {"today": sum(m["leadsToday"] for m in monitors_), "week": sum(m["leadsWeek"] for m in monitors_),
                       "running": sum(1 for m in monitors_ if m["running"] and not m.get("manual")),
                       "count": sum(1 for m in monitors_ if not m.get("manual"))}}


# ---------- jobs ----------
def jobs():
    t0 = today()
    r = seeded("jobs", t0.isoformat())
    matches_src = [
        ("Graduate Data Analyst", "Northwind Analytics", "London · Hybrid", "£30,000", 10, "LinkedIn", 0),
        ("Business Analyst", "Lakeside Group", "Manchester · Hybrid", "£32,000", 10, "Indeed", 0),
        ("Sales Development Representative", "Brightwave Software", "London", "£28,000 + OTE", 9, "Otta", 1),
        ("Junior Insights Analyst", "Contoso Retail", "Remote UK", "£29,500", 9, "Totaljobs", 1),
        ("Graduate Commercial Analyst", "Fabrikam Foods", "Leeds · Hybrid", "£31,000", 9, "Reed", 2),
        ("Business Development Representative", "Bluebird Payments", "London · Hybrid", "£30,000 + OTE", 9, "Glassdoor", 3),
        ("Operations Analyst", "Harbour Logistics", "Birmingham", "£29,000", 9, "CV-Library", 4),
        ("Graduate Data Analyst", "Tailspin Travel", "Bristol · Hybrid", "£28,500", 9, "Guardian Jobs", 5),
    ]
    matches = [{"title": t, "company": c, "location": loc, "salary": sal, "rating": rt, "source": src,
                "url": "https://www.example.com/jobs/demo-" + str(i), "found": str(t0 - timedelta(days=d))}
               for i, (t, c, loc, sal, rt, src, d) in enumerate(matches_src)]
    in_process = [
        {"company": "Northwind Analytics", "role": "Graduate Data Analyst", "status": "Interview", "deadline": str(t0 + timedelta(days=2)), "notes": "45-min video interview with the analytics lead. Prepare SQL examples."},
        {"company": "Lakeside Group", "role": "Business Analyst", "status": "Online assessment", "deadline": str(t0 + timedelta(days=1)), "notes": "Numerical and situational judgement tests."},
        {"company": "Brightwave Software", "role": "Graduate SDR", "status": "Assessment centre", "deadline": str(t0 + timedelta(days=10)), "notes": ""},
        {"company": "Contoso Retail", "role": "Junior Insights Analyst", "status": "Phone screening", "deadline": "", "notes": "Recruiter call went well, waiting on next steps."},
    ]
    recent_src = [(0, "Northwind Analytics", "Graduate Data Analyst", "Interview booked"), (0, "Harbour Logistics", "Operations Analyst", "Applied"),
                  (1, "Lakeside Group", "Business Analyst", "Online assessment received"), (1, "Tailspin Travel", "Graduate Data Analyst", "Applied"),
                  (2, "Woodgrove Bank", "Graduate Analyst", "Rejected"), (2, "Bluebird Payments", "BDR", "Applied"),
                  (3, "Contoso Retail", "Junior Insights Analyst", "Phone screening"), (4, "Fabrikam Foods", "Commercial Analyst", "Waiting for reply"),
                  (5, "Litware Media", "Marketing Analyst", "Denied")]
    recent = [{"date": str(t0 - timedelta(days=d)), "company": c, "role": ro, "change": ch} for d, c, ro, ch in recent_src]
    days30 = [t0 - timedelta(days=n) for n in range(29, -1, -1)]
    applied30 = [0 if d.weekday() == 6 else r.choice([0, 1, 1, 2, 2, 3, 4]) for d in days30]
    applied_week = sum(applied30[-7:])
    return {
        "configured": True, "updated": hm(), "site": "https://job-dashboard.example.com/",
        "counts": {"scraped": 4218, "open": 186, "foundToday": 23, "foundWeek": 141, "goodWeek": 12, "goodToday": 2, "topTotal": 37,
                   "applications": 64, "appliedWeek": applied_week},
        "pipeline": [{"label": "Top matches · 7d", "n": 12}, {"label": "Applied", "n": 64}, {"label": "Awaiting reply", "n": 31},
                     {"label": "In process", "n": 4}, {"label": "Offers", "n": 0}, {"label": "Rejected", "n": 29}],
        "matches": matches, "inProcess": in_process,
        "deadlines": [{"company": x["company"], "role": x["role"], "status": x["status"], "deadline": x["deadline"],
                       "days": (date.fromisoformat(x["deadline"]) - t0).days} for x in in_process if x["deadline"]],
        "recent": recent, "appliedLabels": [label(d) for d in days30], "applied30": applied30,
    }


# ---------- claims (ReclaimHQ-shaped) ----------
def reclaim():
    t0 = today()
    return {
        "configured": True, "updated": hm(), "errors": [],
        "dashboard": {"recovered30": 186.4, "atRisk14": 312.9, "atRiskNote": "3 items need action", "openOrders": 4,
                      "radar": [{"title": "Robot Window Cleaner, Compact", "asin": "DEMOAG1H2J", "value": 139.0, "days": 3},
                                {"title": "Hair Styler Multi-Attachment Set", "asin": "DEMO7X5Y6Z", "value": 112.5, "days": 9}],
                      "radarNote": "2 need action", "leakShortfall": 74.35, "leakNote": "3 leaks", "expiredWinnable": None,
                      "recoveredAllTime": 2148.6, "nextAction": "Assess removal order", "lastSynced": "today 07:40"},
        "claimCounts": {"all": 18, "actionRequired": 1, "active": 3, "won": 13, "lost": 1, "recovered": 1962.2},
        "claims": [
            {"product": "Noise Cancelling Wireless Headphones, Midnight", "order": "Removal DEMO-RM-1042", "status": "Action required", "caseId": "DEMO-CASE-7781", "expiryDays": 6, "value": "£61.40", "image": None},
            {"product": "Air Fryer 5.5L Digital, Black", "order": "Inbound DEMO-IB-221", "status": "Under review", "caseId": "DEMO-CASE-7764", "expiryDays": 21, "value": "£48.99", "image": None},
            {"product": "Smart Plug Mini 4-Pack, Wi-Fi", "order": "Inbound DEMO-IB-219", "status": "Active", "caseId": "DEMO-CASE-7750", "expiryDays": None, "value": "£27.98", "image": None},
            {"product": "Electric Toothbrush Twin Pack", "order": "Removal DEMO-RM-1031", "status": "Won", "caseId": "DEMO-CASE-7702", "expiryDays": None, "value": "£44.99", "image": None},
            {"product": "Family Board Game: Island Explorers", "order": "Inbound DEMO-IB-204", "status": "Lost", "caseId": "DEMO-CASE-7688", "expiryDays": None, "value": "£17.50", "image": None},
        ],
        "leakStats": {"total": 3, "shortfall": 74.35, "openCases": 1, "recovered": 22.1},
        "leaks": [
            {"product": "Cordless Stick Vacuum, 2-in-1 Lightweight", "reimbursementId": "DEMO-RB-55102", "date": str(t0 - timedelta(days=12)), "reimbursed": 71.2, "cog": 99.0, "shortfall": 27.8, "expiresDays": 18, "status": "Detected"},
            {"product": "Kids' Smartwatch with Camera, Blue", "reimbursementId": "DEMO-RB-55087", "date": str(t0 - timedelta(days=20)), "reimbursed": 22.4, "cog": 44.99, "shortfall": 22.59, "expiresDays": 10, "status": "Verified"},
            {"product": "Stainless Steel Insulated Bottle 750ml", "reimbursementId": "DEMO-RB-55011", "date": str(t0 - timedelta(days=33)), "reimbursed": 6.04, "cog": 13.99, "shortfall": 7.95, "expiresDays": 45, "status": "Case open"},
        ],
        "ordersStats": {"totalOrders": 27, "totalItems": 64, "activeClaims": 3, "atRisk": 312.9},
        "expiring": [
            {"orderId": "DEMO-RM-1042", "detail": "3 items · 1 unaccounted", "status": "Completed", "cases": 1, "created": str(t0 - timedelta(days=46)), "deadlineDays": 6, "link": "/orders"},
            {"orderId": "DEMO-RM-1047", "detail": "2 items · 2 unaccounted", "status": "Completed", "cases": 0, "created": str(t0 - timedelta(days=50)), "deadlineDays": 3, "link": "/orders"},
        ],
    }


def health():
    n = now()
    keys = ["fba", "reclaim", "jobs", "isa", "monitors", "calendar", "important", "otp", "purchases"]
    offsets = {"fba": 240, "reclaim": 600, "jobs": 300, "isa": 180, "monitors": 40, "calendar": 200, "important": 120, "otp": 30, "purchases": 420}
    return {"status": "ok", "demo": True, "started": STARTED.strftime("%Y-%m-%dT%H:%M:%S"),
            "checked": {k: (n - timedelta(seconds=offsets[k])).strftime("%Y-%m-%dT%H:%M:%S") for k in keys},
            "errors": {k: False for k in keys}}


def deadlines():
    n = now()
    return {"lastRun": iso(n - timedelta(minutes=18)), "lastResult": {"added": 1, "updated": 0, "errors": []},
            "events": [{"title": "Energy bill Direct Debit", "start": str(today() + timedelta(days=14)), "type": "bill", "who": "Example Energy",
                        "account": "demo@example.com", "subject": "Your bill is ready", "link": "https://mail.google.com/"}]}


DEMO_CHAT = ("This is **demo mode**, so I'm not connected to a model or any real data. In the real Command Centre, Ask mode sends your "
             "question plus a JSON snapshot of the dashboard to the local Claude CLI and Edit mode changes the front-end with a backup and undo.")


# ---------- HTTP ----------
class Handler(SimpleHTTPRequestHandler):
    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, where):
        self.send_response(302)
        self.send_header("Location", where)
        self.end_headers()

    def do_GET(self):
        p = self.path
        if not p.startswith("/api/"):
            return super().do_GET()
        if p.startswith("/api/health"):
            return self.send_json(health())
        if p.startswith("/api/isa/holdings"):
            return self.send_json(isa_holdings())
        if p.startswith("/api/bank/connect") or p.startswith("/api/bank/callback"):
            return self.redirect("/#money?msg=" + quote("Demo mode: bank connections are switched off"))
        if p.startswith("/api/deadlines"):
            return self.send_json(deadlines())
        if p.startswith("/api/insights"):
            return self.send_json(insights())
        if p.startswith("/api/money"):
            return self.send_json(money())
        if p.startswith("/api/bank"):
            return self.send_json({"configured": True, "sandbox": False, "connections": [], "sources": [], "errors": []})
        if p.startswith("/api/purchases"):
            return self.send_json(purchases())
        if p.startswith("/api/otp"):
            return self.send_json(otp())
        if p.startswith("/api/important"):
            return self.send_json(important())
        if p.startswith("/api/calendar"):
            return self.send_json(calendar())
        if p.startswith("/api/monitors"):
            return self.send_json(monitors())
        if p.startswith("/api/isa"):
            return self.send_json(isa())
        if p.startswith("/api/jobs"):
            return self.send_json(jobs())
        if p.startswith("/api/reclaim"):
            return self.send_json(reclaim())
        if p.startswith("/api/fba/range"):
            qs = parse_qs(urlparse(p).query)
            try:
                frm, to = date.fromisoformat(qs["from"][0]), date.fromisoformat(qs["to"][0])
            except (KeyError, ValueError):
                return self.send_json({"error": "Pick a valid date range."})
            if (to - frm).days > 800:
                frm = to - timedelta(days=800)
            return self.send_json(range_data(frm, to))
        if p.startswith("/api/fba"):
            return self.send_json(fba())
        return self.send_json({"error": "unknown endpoint"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            body = {}
        p = self.path
        if p.startswith("/api/chat/undo"):
            return self.send_json({"ok": True})
        if p.startswith("/api/chat"):
            if body.get("mode") == "edit":
                return self.send_json({"ok": True, "text": DEMO_CHAT + "\n\nNo files were changed.", "changed": []})
            return self.send_json({"ok": True, "text": DEMO_CHAT})
        if p.startswith("/api/purchases/note"):
            return self.send_json({"ok": True, "text": str(body.get("text", "")).strip(), "at": iso(now())})
        if p.startswith("/api/isa/holdings"):
            return self.send_json({"ok": True, "isa": isa()})
        if p.startswith("/api/"):
            return self.send_json({"ok": True})
        self.send_error(404)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), partial(Handler, directory=str(APP_DIR)))
    print(f"Command Centre DEMO running at http://{HOST}:{PORT}/  (fake data, Ctrl+C to stop)")
    if "--open" in sys.argv:
        import webbrowser
        webbrowser.open(f"http://{HOST}:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
