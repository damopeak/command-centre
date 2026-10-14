"""Invenno connector for the Sales page.

Invenno (app.invenno.co.uk) already calculates profit with your costs, fees, VAT and refunds,
so the dashboard reads the same JSON its own dashboard uses, through a saved browser login.

First-time setup (opens a browser window, you log in yourself, it closes when done):
    python invenno.py --login
Test a refresh:
    python invenno.py
"""
import json
import time
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from spapi import uk_now, uk_offset

ROOT = Path(__file__).parent
PROFILE_DIR = str(ROOT / "invenno_profile")
APP_URL = "https://app.invenno.co.uk/"
PROBE = "/api/v1/statistics/p-l"


def _ctx(pw, headless):
    return pw.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR, headless=headless, viewport={"width": 1400, "height": 900},
    )


def _uk_midnight_utc(d):
    """UTC ISO string for 00:00 UK time on date d."""
    naive = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return (naive - uk_offset(naive)).isoformat().replace("+00:00", "Z")


def _pct(cur, prev):
    """Real % change. (Invenno's own percentageChange field is current as a % of previous.)"""
    if cur is None or not prev:
        return None
    return round((cur - prev) / abs(prev) * 100, 1)


def _fetch_all(page, urls):
    return page.evaluate(
        """async (urls) => {
            const out = {};
            for (const [k, u] of Object.entries(urls)) {
                try {
                    const r = await fetch(u, { credentials: "include" });
                    out[k] = r.ok ? await r.json() : { __status: r.status };
                } catch (e) { out[k] = { __error: String(e) }; }
            }
            return out;
        }""",
        urls,
    )


def logged_in(page):
    status = page.evaluate(f"""async () => (await fetch("{PROBE}?from=2020-01-01T00:00:00Z&to=2020-01-02T00:00:00Z", {{credentials: "include"}})).status""")
    return status == 200


def login():
    with _pw_lock, sync_playwright() as pw:
        ctx = _ctx(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(APP_URL)
        print("Log in to Invenno in the window that opened. It will close by itself once you're in.")
        for _ in range(600):  # up to 10 minutes
            page.wait_for_timeout(1000)
            try:
                if "invenno.co.uk" in page.url and logged_in(page):
                    print("Logged in — session saved.")
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass
        ctx.close()


def build_fba():
    if not Path(PROFILE_DIR).exists():
        return {"configured": False, "needsLogin": True}

    now = uk_now()
    today = now.date()
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    t0 = _uk_midnight_utc(today)
    y0 = _uk_midnight_utc(today - timedelta(days=1))
    m0 = _uk_midnight_utc(today.replace(day=1))
    d30 = _uk_midnight_utc(today - timedelta(days=29))

    urls = {
        "today": f"/api/v1/statistics/p-l?from={t0}&to={now_utc}&dropdownText=Today",
        "yesterday": f"/api/v1/statistics/p-l?from={y0}&to={t0}&dropdownText=Yesterday",
        "month": f"/api/v1/statistics/p-l?from={m0}&to={now_utc}&dropdownText=This%20month",
        "d30": f"/api/v1/statistics/p-l?from={d30}&to={now_utc}&dropdownText=Last%2030%20days",
        "daily": f"/api/v1/statistics/daily-profit-loss?from={d30}&to={now_utc}",
        "top": f"/api/v1/statistics/metrics/top-sellers?from={today - timedelta(days=29)}&to={today}&sortBy=profit&groupBy=asin&limit=10",
        "inventory": "/api/v1/inventory/summary",
        "alerts": "/api/v1/purchases/sku-stock-alerts",
        "projection": "/api/v1/statistics/month-projection",
    }

    with _pw_lock, sync_playwright() as pw:
        ctx = _ctx(pw, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)  # let the app refresh its session token
            if not logged_in(page):
                return {"configured": False, "needsLogin": True}
            raw = _fetch_all(page, urls)
            _capture_session(ctx, page)
        finally:
            ctx.close()

    errors = [f"Invenno {k} returned {v.get('__status') or v.get('__error')}" for k, v in raw.items()
              if isinstance(v, dict) and ("__status" in v or "__error" in v)]

    def cur(key):
        return (raw.get(key) or {}).get("current") or {}

    def prev(key):
        return (raw.get(key) or {}).get("previous") or {}

    t, m, y, d = cur("today"), cur("month"), cur("yesterday"), cur("d30")
    daily = (raw.get("daily") or {}).get("dailyData") or []
    proj = ((raw.get("projection") or {}).get("overall") or {}).get("metrics") or {}
    inv = ((raw.get("inventory") or {}).get("table") or {}).get("all") or {}

    top = []
    for it in (raw.get("top") or {}).get("items") or []:
        top.append({
            "asin": it.get("asin"), "sku": it.get("sku"), "title": it.get("title"), "image": it.get("imageUrl"),
            "units": it.get("units"), "sales": it.get("sales"), "profit": it.get("profit"),
            "roi": round(it["roi"]) if it.get("roi") is not None else None, "margin": it.get("margin"), "stock": None,
        })

    alerts = []
    for a in (raw.get("alerts") or [])[:6] if isinstance(raw.get("alerts"), list) else []:
        title = a.get("title") or a.get("productName") or a.get("sku") or "Stock alert"
        alerts.append({"type": "amber", "title": str(title)[:70], "meta": a.get("message") or a.get("reason") or ""})

    return {
        "configured": True,
        "source": "invenno",
        "updated": now.strftime("%H:%M"),
        "errors": errors,
        "hasCosts": True,
        "today": {"sales": t.get("totalSales", 0), "profit": t.get("totalProfit", 0), "units": t.get("totalUnitsSold", 0),
                  "orders": t.get("totalOrders", 0), "margin": t.get("totalMargin"), "roi": t.get("roi")},
        "yesterday": {"sales": y.get("totalSales", 0), "profit": y.get("totalProfit", 0), "units": y.get("totalUnitsSold", 0),
                      "margin": y.get("totalMargin"), "roi": y.get("roi"), "orders": y.get("totalOrders", 0),
                      "refunds": y.get("totalRefunds", 0)},
        "month": {"sales": m.get("totalSales", 0), "profit": m.get("totalProfit", 0), "units": m.get("totalUnitsSold", 0),
                  "margin": m.get("totalMargin"), "roi": m.get("roi"),
                  "profitChange": _pct(m.get("totalProfit"), prev("month").get("totalProfit")),
                  "salesChange": _pct(m.get("totalSales"), prev("month").get("totalSales")),
                  "projectedProfit": (proj.get("profit") or {}).get("expected"),
                  "projectedSales": (proj.get("sales") or {}).get("expected")},
        "d30": {"sales": d.get("totalSales", 0), "profit": d.get("totalProfit", 0), "units": d.get("totalUnitsSold", 0),
                "margin": d.get("totalMargin"), "roi": d.get("roi"), "refunds": d.get("totalRefunds", 0)},
        "labels": [x.get("label") for x in daily],
        "dates": [x.get("date") for x in daily],
        "sales30": [round(x.get("sales") or 0, 2) for x in daily],
        "profit30": [round(x.get("profit") or 0, 2) for x in daily],
        "units30": [x.get("units") or 0 for x in daily],
        "topProducts": top,
        "alerts": alerts,
        "inventory": {"units": inv.get("units"), "cost": inv.get("cost"), "resale": inv.get("resale"), "profit": inv.get("profit"), "roi": inv.get("roi")},
    }


# ---------- Fast queries for any date range (plain HTTP with the saved session) ----------
class _ProfileLock:
    """Only one user of the Invenno browser profile at a time, across threads AND processes
    (dashboard server, one-off scripts, connect-invenno.bat). Two at once can rotate the
    login token twice and get the session revoked."""
    def __init__(self):
        self._t = threading.Lock()
        self._f = None

    def __enter__(self):
        import msvcrt
        self._t.acquire()
        self._f = open(ROOT / "invenno_profile.lock", "a+")
        deadline = time.time() + 300
        while True:
            try:
                self._f.seek(0)
                msvcrt.locking(self._f.fileno(), msvcrt.LK_NBLCK, 1)
                return self
            except OSError:
                if time.time() > deadline:
                    self._f.close(); self._t.release()
                    raise RuntimeError("Invenno profile busy (another process is using it)")
                time.sleep(1)

    def __exit__(self, *exc):
        import msvcrt
        try:
            self._f.seek(0)
            msvcrt.locking(self._f.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self._f.close(); self._t.release()


_pw_lock = _ProfileLock()   # the browser profile can only be open once at a time
_session = {"cookie": None, "ua": None}


class NeedsLogin(Exception):
    pass


def _capture_session(ctx, page):
    cookies = ctx.cookies("https://app.invenno.co.uk")
    _session["cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    _session["ua"] = page.evaluate("navigator.userAgent")


def refresh_session():
    """Open the saved profile headlessly so Invenno renews its token, then keep the cookies."""
    with _pw_lock, sync_playwright() as pw:
        ctx = _ctx(pw, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            if not logged_in(page):
                raise NeedsLogin()
            _capture_session(ctx, page)
        finally:
            ctx.close()


def browser_get(paths):
    """Fetch several Invenno API paths through the saved browser profile.

    Everything goes through this one browser so Invenno's single-use refresh token is only ever
    rotated (and saved) in one place. Direct HTTP calls with copied cookies rotated the token
    server-side, threw the new one away and got the whole session revoked ("keeps logging out").
    """
    with _pw_lock, sync_playwright() as pw:
        ctx = _ctx(pw, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            if not logged_in(page):
                raise NeedsLogin()
            raw = _fetch_all(page, paths)
        finally:
            ctx.close()
    for k, v in raw.items():
        if isinstance(v, dict) and v.get("__status") in (401, 403):
            raise NeedsLogin()
        if isinstance(v, dict) and ("__status" in v or "__error" in v):
            raise RuntimeError(f"Invenno {k} returned {v.get('__status') or v.get('__error')}")
    return raw


_range_cache = {}


def api_get(path, _retry=True):  # legacy direct-HTTP path; not used any more (see browser_get)
    if not _session["cookie"]:
        refresh_session()
    req = urllib.request.Request("https://app.invenno.co.uk" + path, headers={
        "Cookie": _session["cookie"], "User-Agent": _session["ua"] or "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and _retry:
            refresh_session()
            return api_get(path, _retry=False)
        if e.code in (401, 403):
            raise NeedsLogin() from e
        raise


def range_data(frm, to):
    """Totals, previous-period comparison, daily series and top sellers for UK dates frm..to inclusive."""
    today = uk_now().date()
    start = _uk_midnight_utc(frm)
    end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if to >= today else _uk_midnight_utc(to + timedelta(days=1))
    q = urllib.parse.quote
    # Past ranges don't change much: cache 30 min; ranges including today: 3 min
    key, ttl = (str(frm), str(to)), (180 if to >= today else 1800)
    hit = _range_cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    raw = browser_get({
        "pl": f"/api/v1/statistics/p-l?from={q(start)}&to={q(end)}&dropdownText=Custom",
        "daily": f"/api/v1/statistics/daily-profit-loss?from={q(start)}&to={q(end)}",
        "top": f"/api/v1/statistics/metrics/top-sellers?from={frm}&to={to}&sortBy=profit&groupBy=asin&limit=10",
    })
    pl, daily, top = raw["pl"], raw["daily"].get("dailyData") or [], raw["top"].get("items") or []
    c, p = pl.get("current") or {}, pl.get("previous") or {}
    pick = lambda d: {"sales": d.get("totalSales", 0), "profit": d.get("totalProfit", 0), "units": d.get("totalUnitsSold", 0),
                      "orders": d.get("totalOrders", 0), "margin": d.get("totalMargin"), "roi": d.get("roi"),
                      "refunds": d.get("totalRefunds", 0)}
    out = {
        "from": str(frm), "to": str(to), "current": pick(c), "previous": pick(p),
        "change": {"profit": _pct(c.get("totalProfit"), p.get("totalProfit")), "sales": _pct(c.get("totalSales"), p.get("totalSales")),
                   "units": _pct(c.get("totalUnitsSold"), p.get("totalUnitsSold"))},
        "labels": [x.get("label") for x in daily], "dates": [x.get("date") for x in daily],
        "sales": [round(x.get("sales") or 0, 2) for x in daily], "profit": [round(x.get("profit") or 0, 2) for x in daily],
        "units": [x.get("units") or 0 for x in daily],
        "topProducts": [{"asin": it.get("asin"), "sku": it.get("sku"), "title": it.get("title"), "image": it.get("imageUrl"),
                         "units": it.get("units"), "sales": it.get("sales"), "profit": it.get("profit"),
                         "roi": round(it["roi"]) if it.get("roi") is not None else None, "margin": it.get("margin")} for it in top],
    }
    _range_cache[key] = (time.time(), out)
    return out


if __name__ == "__main__":
    if "--login" in sys.argv:
        login()
    else:
        print(json.dumps(build_fba(), indent=2)[:3000])
