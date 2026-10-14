"""Amazon Selling Partner API client for the Sales page (UK marketplace, stdlib only).

Credentials come from .env next to this file:
    SP_API_CLIENT_ID, SP_API_CLIENT_SECRET, SP_API_REFRESH_TOKEN
Optional:
    VAT_REGISTERED=true   deduct 1/6 of VAT-inclusive sales as output VAT
Product costs (for profit) come from costs.csv: sku,cost
"""
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
ENDPOINT = "https://sellingpartnerapi-eu.amazon.com"
MARKETPLACE = "A1F83G8C2ARO7P"  # amazon.co.uk
TOKEN_URL = "https://api.amazon.com/auth/o2/token"


def load_env():
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def load_costs():
    path = ROOT / "costs.csv"
    costs = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    sku = row["sku"].strip()
                    if sku and not sku.startswith("EXAMPLE"):
                        costs[sku] = float(row["cost"])
                except (KeyError, ValueError):
                    pass
    return costs


# ---------- UK time without tzdata (Windows Python has no zoneinfo database) ----------
def _last_sunday(year, month):
    d = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year, 12, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def uk_offset(dt_utc):
    start = _last_sunday(dt_utc.year, 3).replace(hour=1, tzinfo=timezone.utc)
    end = _last_sunday(dt_utc.year, 10).replace(hour=1, tzinfo=timezone.utc)
    return timedelta(hours=1) if start <= dt_utc < end else timedelta(0)


def uk_now():
    now = datetime.now(timezone.utc)
    return (now + uk_offset(now)).replace(tzinfo=timezone(uk_offset(now)))


def uk_date(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (dt + uk_offset(dt)).date()


class SPAPIError(Exception):
    pass


class Client:
    def __init__(self, env):
        self.env = env
        self._token = None
        self._expires = 0

    def token(self):
        if self._token and time.time() < self._expires - 60:
            return self._token
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.env["SP_API_REFRESH_TOKEN"],
            "client_id": self.env["SP_API_CLIENT_ID"],
            "client_secret": self.env["SP_API_CLIENT_SECRET"],
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            raise SPAPIError(f"Login with Amazon rejected the credentials ({e.code}). Check the three values in .env.") from e
        self._token = data["access_token"]
        self._expires = time.time() + data.get("expires_in", 3600)
        return self._token

    def get(self, path, params):
        url = f"{ENDPOINT}{path}?{urllib.parse.urlencode(params, doseq=True)}"
        for attempt in range(6):
            req = urllib.request.Request(url, headers={"x-amz-access-token": self.token(), "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(2 * (attempt + 1))
                    continue
                detail = e.read().decode(errors="ignore")[:300]
                if e.code == 403:
                    raise SPAPIError(f"Access denied to {path} — the app may be missing a role in Seller Central. {detail}") from e
                raise SPAPIError(f"{path} returned {e.code}: {detail}") from e
        raise SPAPIError(f"{path} kept being rate-limited")


# ---------- Data pulls ----------
def order_metrics(client, days):
    """Daily sales/units for the last `days` UK days, including today (near real-time)."""
    now = uk_now()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(microsecond=0) + timedelta(minutes=1)
    data = client.get("/sales/v1/orderMetrics", {
        "marketplaceIds": MARKETPLACE,
        "interval": f"{start.isoformat()}--{end.isoformat()}",
        "granularity": "Day",
        "granularityTimeZone": "Europe/London",
    })
    out = []
    for row in data.get("payload", []):
        out.append({
            "date": row["interval"][:10],
            "sales": float(row["totalSales"]["amount"]),
            "units": int(row["unitCount"]),
            "orders": int(row["orderCount"]),
        })
    return out


def inventory(client):
    items, token = [], None
    while True:
        params = {"granularityType": "Marketplace", "granularityId": MARKETPLACE, "marketplaceIds": MARKETPLACE, "details": "true"}
        if token:
            params["nextToken"] = token
        data = client.get("/fba/inventory/v1/summaries", params)
        for s in data.get("payload", {}).get("inventorySummaries", []):
            d = s.get("inventoryDetails") or {}
            items.append({
                "sku": s.get("sellerSku"), "asin": s.get("asin"), "title": s.get("productName") or s.get("sellerSku"),
                "available": d.get("fulfillableQuantity", 0),
                "inbound": (d.get("inboundWorkingQuantity", 0) + d.get("inboundShippedQuantity", 0) + d.get("inboundReceivingQuantity", 0)),
                "total": s.get("totalQuantity", 0),
            })
        token = (data.get("pagination") or {}).get("nextToken")
        if not token:
            return items
        time.sleep(0.6)


def _money(lst, key):
    total = 0.0
    for item in lst or []:
        amt = item.get(key, {}).get("CurrencyAmount")
        if amt is not None:
            total += float(amt)
    return total


def financial_events(client, days):
    """Settled sales, fees and refunds per day and per SKU from the Finances API."""
    after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    params = {"PostedAfter": after, "MaxResultsPerPage": 100}
    per_day = defaultdict(lambda: {"sales": 0.0, "fees": 0.0, "refunds": 0.0, "units": 0})
    per_sku = defaultdict(lambda: {"units": 0, "sales": 0.0, "fees": 0.0, "title": None})
    while True:
        data = client.get("/finances/v0/financialEvents", params)
        payload = data.get("payload", {})
        ev = payload.get("FinancialEvents", {})
        for sh in ev.get("ShipmentEventList", []):
            day = str(uk_date(sh["PostedDate"]))
            for it in sh.get("ShipmentItemList", []):
                sales = _money(it.get("ItemChargeList"), "ChargeAmount")
                fees = -_money(it.get("ItemFeeList"), "FeeAmount")
                qty = int(it.get("QuantityShipped", 0))
                sku = it.get("SellerSKU", "?")
                per_day[day]["sales"] += sales
                per_day[day]["fees"] += fees
                per_day[day]["units"] += qty
                per_sku[sku]["units"] += qty
                per_sku[sku]["sales"] += sales
                per_sku[sku]["fees"] += fees
        for rf in ev.get("RefundEventList", []):
            day = str(uk_date(rf["PostedDate"]))
            for it in rf.get("ShipmentItemAdjustmentList", []):
                per_day[day]["refunds"] += -(_money(it.get("ItemChargeAdjustmentList"), "ChargeAmount")
                                             + _money(it.get("ItemFeeAdjustmentList"), "FeeAmount"))
        token = payload.get("NextToken")
        if not token:
            return per_day, per_sku
        params = {"NextToken": token}
        time.sleep(2.1)  # 0.5 requests/second limit


# ---------- Assemble the dashboard payload ----------
def build_fba():
    env = load_env()
    keys = ("SP_API_CLIENT_ID", "SP_API_CLIENT_SECRET", "SP_API_REFRESH_TOKEN")
    if not all(env.get(k) and not env[k].startswith("paste") for k in keys):
        return {"configured": False}

    client = Client(env)
    vat = env.get("VAT_REGISTERED", "").lower() in ("1", "true", "yes")
    costs = load_costs()
    result = {"configured": True, "updated": uk_now().strftime("%H:%M"), "errors": [], "hasCosts": bool(costs), "vat": vat}

    metrics = []
    try:
        metrics = order_metrics(client, 30)
    except SPAPIError as e:
        result["errors"].append(str(e))

    per_day, per_sku = {}, {}
    try:
        per_day, per_sku = financial_events(client, 30)
    except SPAPIError as e:
        result["errors"].append(str(e))

    inv = []
    try:
        inv = inventory(client)
    except SPAPIError as e:
        result["errors"].append(str(e))

    # Margin from settled finances: (sales - fees - refunds - VAT - cost) / sales
    def profit_of(sales, fees, refunds, cost):
        p = sales - fees - refunds - cost
        return p - sales / 6 if vat else p

    inv_by_sku = {i["sku"]: i for i in inv}
    top = []
    for sku, s in per_sku.items():
        cost = costs.get(sku, 0) * s["units"] if costs else 0
        prof = profit_of(s["sales"], s["fees"], 0, cost) if costs else None
        i = inv_by_sku.get(sku, {})
        top.append({
            "sku": sku, "asin": i.get("asin", ""), "title": i.get("title") or sku, "units": s["units"],
            "sales": round(s["sales"], 2), "fees": round(s["fees"], 2),
            "profit": round(prof, 2) if prof is not None else None,
            "roi": round(prof / cost * 100) if prof is not None and cost else None,
            "stock": i.get("available"),
        })
    top.sort(key=lambda t: (t["profit"] if t["profit"] is not None else t["sales"]), reverse=True)
    result["topProducts"] = top[:10]

    # Daily series (last 30 UK days)
    today = uk_now().date()
    dates = [str(today - timedelta(days=n)) for n in range(29, -1, -1)]
    by_date = {m["date"]: m for m in metrics}
    result["labels"] = dates
    result["sales30"] = [round(by_date.get(d, {}).get("sales", 0), 2) for d in dates]
    result["units30"] = [by_date.get(d, {}).get("units", 0) for d in dates]

    fin_sales = sum(v["sales"] for v in per_day.values())
    fin_cost = sum(costs.get(sku, 0) * s["units"] for sku, s in per_sku.items()) if costs else 0
    fin_profit = sum(profit_of(v["sales"], v["fees"], v["refunds"], 0) for v in per_day.values()) - fin_cost
    margin = (fin_profit / fin_sales) if (fin_sales and costs) else None
    result["margin"] = round(margin * 100, 1) if margin is not None else None
    result["profit30"] = [round(s * margin, 2) for s in result["sales30"]] if margin is not None else None

    month_prefix = str(today)[:7]
    month_sales = sum(m["sales"] for m in metrics if m["date"].startswith(month_prefix))
    t, y = by_date.get(str(today), {}), by_date.get(str(today - timedelta(days=1)), {})
    result["today"] = {"sales": round(t.get("sales", 0), 2), "units": t.get("units", 0), "orders": t.get("orders", 0),
                       "profit": round(t.get("sales", 0) * margin, 2) if margin is not None else None}
    result["yesterday"] = {"sales": round(y.get("sales", 0), 2)}
    result["month"] = {"sales": round(month_sales, 2), "units": sum(m["units"] for m in metrics if m["date"].startswith(month_prefix)),
                       "profit": round(month_sales * margin, 2) if margin is not None else None}
    result["fees30"] = round(sum(v["fees"] for v in per_day.values()), 2)
    result["refunds30"] = round(sum(v["refunds"] for v in per_day.values()), 2)

    # Stock alerts: sellers with < 7 days of cover at their 30-day sales rate
    alerts = []
    for sku, s in per_sku.items():
        i = inv_by_sku.get(sku)
        if not i or not s["units"]:
            continue
        per_day_rate = s["units"] / 30
        cover = i["available"] / per_day_rate if per_day_rate else 99
        if i["available"] == 0:
            alerts.append({"type": "red", "title": f"{i['title'][:60]} is out of stock", "meta": f"Sold {s['units']} in 30 days · {i['inbound']} inbound"})
        elif cover < 7:
            alerts.append({"type": "amber", "title": f"{i['title'][:60]} — {i['available']} left", "meta": f"~{cover:.0f} days of cover · {i['inbound']} inbound"})
    result["alerts"] = alerts[:6]
    return result


if __name__ == "__main__":
    print(json.dumps(build_fba(), indent=2)[:4000])
