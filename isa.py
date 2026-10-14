"""Stocks & Shares ISA: your Vanguard holdings (holdings.json) valued at live public prices.

ETFs   -> Yahoo Finance (live during LSE hours)
Funds  -> Financial Times tearsheet (daily NAV, the same price Vanguard uses)
No login to Vanguard is needed. Update units in holdings.json (or from the ISA page) after you buy.
Test:  python isa.py
"""
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from spapi import uk_now

ROOT = Path(__file__).parent
HOLDINGS = ROOT / "holdings.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


def _get(url, as_json=True):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        body = r.read().decode("utf-8", "ignore")
    return json.loads(body) if as_json else body


def yahoo(symbol, rng="6mo"):
    """Latest price, previous close and daily closes."""
    res = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={rng}&interval=1d")["chart"]["result"][0]
    meta = res["meta"]
    closes = res["indicators"]["quote"][0]["close"]
    days = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in res["timestamp"]]
    hist = {d: c for d, c in zip(days, closes) if c is not None}
    try:  # Yahoo's daily series sometimes drops a recent day (e.g. Mon 12 Oct 2026); fill it from hourly bars
        r5 = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=60m")["chart"]["result"][0]
        for t, c in zip(r5["timestamp"], r5["indicators"]["quote"][0]["close"]):
            d = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
            if c is not None and d not in hist:
                hist.setdefault("_fill", {})[d] = c   # last hourly close of that day wins
        for d, c in hist.pop("_fill", {}).items():
            hist[d] = c
    except Exception:
        pass
    price = meta.get("regularMarketPrice")
    ordered = [hist[d] for d in sorted(hist)]
    # previous close = last close before today's price (Yahoo's chartPreviousClose is the start of the range)
    prev = ordered[-2] if len(ordered) >= 2 and abs(ordered[-1] - price) <= max(1e-3, price * 1e-4) else (ordered[-1] if ordered else None)
    when = datetime.fromtimestamp(meta.get("regularMarketTime", time.time()), timezone.utc)
    return {"price": price, "prev": prev, "history": hist, "time": when.isoformat()}


def ft(isin):
    html = _get(f"https://markets.ft.com/data/funds/tearsheet/summary?s={isin}:GBP", as_json=False)
    price = re.search(r'Price \(GBP\)</span><span class="mod-ui-data-list__value">([\d,.]+)</span>', html)
    change = re.search(r"Today's Change</span><span class=\"mod-ui-data-list__value\"><span class=\"mod-format--(pos|neg|neutral)[^\"]*\">(?:<i[^>]*></i>)?\s*(-?[\d,.]+)\s*/", html)
    asof = re.search(r"as of ([A-Z][a-z]{2} \d{2} \d{4})", html)
    if not price:
        raise ValueError(f"FT price not found for {isin}")
    p = float(price.group(1).replace(",", ""))
    ch = float(change.group(2).replace(",", "")) if change else 0.0
    if change and change.group(1) == "neg" and ch > 0:
        ch = -ch
    return {"price": p, "prev": p - ch, "asOf": asof.group(1) if asof else None}


def load_holdings():
    return json.loads(HOLDINGS.read_text(encoding="utf-8"))


def save_holdings(data):
    HOLDINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build():
    cfg = load_holdings()
    errors, rows, histories = [], [], {}
    for h in cfg["holdings"]:
        try:
            if h["source"] == "yahoo":
                q = yahoo(h["symbol"])
                histories[h["ticker"]] = q["history"]
                priced_at = "live"
            else:
                q = ft(h["isin"])
                priced_at = q.get("asOf") or "daily"
                if h.get("historySymbol"):
                    try:
                        histories[h["ticker"]] = yahoo(h["historySymbol"])["history"]
                    except Exception:
                        pass
        except Exception as e:
            errors.append(f"No price for {h['ticker']}: {e}")
            fallback = float(h["totalCost"]) / float(h["units"]) if h.get("totalCost") and h.get("units") else h.get("avgCost", 0)
            q, priced_at = {"price": h.get("lastPrice") or fallback, "prev": None}, "stale"
        units, price = float(h["units"]), float(q["price"])
        # Vanguard's exact total cost (its average unit cost is rounded to the penny)
        cost = float(h["totalCost"]) if "totalCost" in h else units * float(h["avgCost"])
        value = units * price
        day = units * (price - q["prev"]) if q.get("prev") else 0.0
        rows.append({
            "ticker": h["ticker"], "name": h["name"], "units": units, "avgCost": round(cost / units, 2) if units else 0, "price": round(price, 4),
            "value": round(value, 2), "cost": round(cost, 2), "gain": round(value - cost, 2),
            "gainPct": round((value - cost) / cost * 100, 2) if cost else 0, "day": round(day, 2),
            "dayPct": round((price - q["prev"]) / q["prev"] * 100, 2) if q.get("prev") else 0.0,
            "ocf": h.get("ocf"), "priced": priced_at,
        })

    cash = float(cfg.get("cash", 0))
    total = sum(r["value"] for r in rows) + cash
    invested = sum(r["cost"] for r in rows) + cash
    day = sum(r["day"] for r in rows)
    for r in rows:
        r["weight"] = round(r["value"] / total * 100, 2) if total else 0
    rows.sort(key=lambda r: r["value"], reverse=True)

    # Value of today's holdings over the last 6 months (units held constant)
    dates = sorted(set().union(*[set(hh) for hh in histories.values()])) if histories else []
    series, last = [], {}
    by_ticker = {r["ticker"]: r for r in rows}
    for d in dates:
        v = cash
        for t, r in by_ticker.items():
            hh = histories.get(t, {})
            if d in hh:
                last[t] = hh[d]
            v += r["units"] * last.get(t, r["price"])
        series.append(round(v, 2))
    series.append(round(total, 2))
    dates.append(uk_now().strftime("%Y-%m-%d"))

    weighted_ocf = sum((r["ocf"] or 0) * r["value"] for r in rows) / (total - cash) if total > cash else 0
    return {
        "configured": True, "updated": uk_now().strftime("%H:%M"), "errors": errors,
        "account": cfg.get("account"), "holdingsAsOf": cfg.get("asOf"),
        "value": round(total, 2), "invested": round(invested, 2), "gain": round(total - invested, 2),
        "gainPct": round((total - invested) / invested * 100, 2) if invested else 0,
        "day": round(day, 2), "dayPct": round(day / (total - day) * 100, 2) if total - day else 0,
        "netContributions": cfg.get("netContributions"),
        "return": round(total - cfg["netContributions"], 2) if cfg.get("netContributions") else None,
        "cash": cash, "ocf": round(weighted_ocf, 3), "annualFees": round(weighted_ocf / 100 * (total - cash), 2),
        "holdings": rows, "historyDates": dates, "history": series,
    }


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: v for k, v in d.items() if k not in ("history", "historyDates")}, indent=1)[:3000])
    print("history points:", len(d["history"]), d["history"][:3], d["history"][-3:])
