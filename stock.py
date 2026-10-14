"""Stock ageing from Invenno: what's slow, stuck or tying up money.

Rules chosen by the user ("Standard"):
  * bought but not live after 21 days      (from the Purchases tracker)
  * live but no sales in the last 30 days  (Invenno inventory + 30-day sales per ASIN)
  * still in stock 60+ days after purchase (SKU date / created date)
Unit cost comes from the SKU format the user uses: ASIN-COST-DD/MM/YY-QTY.
"""
import json
import re
from datetime import date, datetime, timedelta

import invenno

NOT_LIVE_DAYS, NO_SALES_DAYS, OLD_DAYS = 21, 30, 60

JS = r"""async (cfg) => {
  const inv = []; let cursor = null, guard = 0;
  while (guard++ < 60) {
    const r = await fetch(`/api/v1/inventory?limit=200${cursor ? "&cursor=" + encodeURIComponent(cursor) : ""}`, { credentials: "include" });
    if (!r.ok) return { error: "inventory " + r.status };
    const d = await r.json();
    for (const x of d.inventory || []) {
      if (x.isDeleted || x.isInactive) continue;
      inv.push({ asin: x.asin, sku: x.sku, title: (x.product || {}).title, image: (x.product || {}).imageUrl, created: x.createdAt,
                 fulfillable: x.fulfillableQuantity || 0, inbound: (x.inboundQuantity || 0) + (x.inboundWorkingQuantity || 0) + (x.inboundShippedQuantity || 0) + (x.inboundReceivingQuantity || 0),
                 reserved: x.totalReservedQuantity || x.reservedQuantity || 0, sold: x.totalSold || 0, received: x.totalReceived || 0,
                 price: x.primaryListingPrice || x.priceAmount, status: x.status, stranded: x.strandedQuantity || 0,
                 unfulfillable: x.totalUnfulfillableQuantity || 0 });
    }
    if (!d.hasNextPage || !d.nextCursor) break;
    cursor = d.nextCursor;
  }
  const sold = {}; let offset = 0;
  while (offset < 3000) {
    const r = await fetch(`/api/v1/statistics/metrics/top-sellers?from=${cfg.from}&to=${cfg.to}&sortBy=units&groupBy=asin&limit=50&offset=${offset}`, { credentials: "include" });
    if (!r.ok) break;
    const items = (await r.json()).items || [];
    for (const it of items) sold[it.asin] = (sold[it.asin] || 0) + (it.units || 0);
    if (items.length < 50) break;
    offset += 50;
  }
  return { inv, sold };
}"""


def _sku_parts(sku):
    m = re.match(r"^([A-Z0-9]{10})-(\d+(?:\.\d+)?)-(\d{2})/(\d{2})/(\d{2})", sku or "")
    if not m:
        return None, None
    try:
        return float(m.group(2)), date(2000 + int(m.group(5)), int(m.group(4)), int(m.group(3)))
    except ValueError:
        return float(m.group(2)), None


def build():
    today = date.today()
    with invenno._pw_lock, invenno.sync_playwright() as pw:
        ctx = invenno._ctx(pw, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(invenno.APP_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            if not invenno.logged_in(page):
                raise invenno.NeedsLogin()
            raw = page.evaluate(JS, {"from": str(today - timedelta(days=NO_SALES_DAYS - 1)), "to": str(today)})
        finally:
            ctx.close()
    if raw.get("error"):
        raise RuntimeError(raw["error"])
    sold30 = raw["sold"]
    rows, no_sales, old = [], [], []
    for x in raw["inv"]:
        cost, bought = _sku_parts(x["sku"])
        if not bought and x.get("created"):
            bought = datetime.fromisoformat(x["created"][:10]).date()
        age = (today - bought).days if bought else None
        stock = x["fulfillable"] + x["reserved"]
        if stock <= 0:
            continue
        r = {**x, "cost": cost, "bought": bought.isoformat() if bought else None, "age": age, "stock": stock,
             "sold30": sold30.get(x["asin"], 0), "tiedUp": round((cost or 0) * stock, 2)}
        rows.append(r)
        if r["sold30"] == 0 and age is not None and age >= NO_SALES_DAYS:
            no_sales.append(r)
        if age is not None and age >= OLD_DAYS:
            old.append(r)
    key = lambda r: -r["tiedUp"]
    return {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "limits": {"notLive": NOT_LIVE_DAYS, "noSales": NO_SALES_DAYS, "old": OLD_DAYS},
            "inStock": len(rows), "stockValue": round(sum(r["tiedUp"] for r in rows), 2),
            "noSales": sorted(no_sales, key=key), "old": sorted(old, key=key),
            "noSalesValue": round(sum(r["tiedUp"] for r in no_sales), 2), "oldValue": round(sum(r["tiedUp"] for r in old), 2)}


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: v for k, v in d.items() if k not in ("noSales", "old")}, indent=1))
    for r in d["noSales"][:10]:
        print("no sales:", r["age"], "d", r["stock"], "units £", r["tiedUp"], r["title"][:50])
    for r in d["old"][:5]:
        print("old:", r["age"], "d", r["stock"], "units sold30", r["sold30"], r["title"][:50])
