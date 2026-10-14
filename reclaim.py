"""ReclaimHQ connector: claims, deadlines and leaks for the Claims page.

ReclaimHQ (reclaimhq.uk) builds its pages in the browser, so this opens them in a saved,
headless browser session and reads the finished tables, exactly as you see them.

First-time setup (opens a window, you log in yourself, it closes when done):
    python reclaim.py --login
Test a refresh:
    python reclaim.py
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from spapi import uk_now

ROOT = Path(__file__).parent
PROFILE_DIR = str(ROOT / "reclaim_profile")
BASE = "https://reclaimhq.uk"

# Reads a table, lining cells up with headers from the right (some rows skip the image cell)
TABLE_JS = """() => {
  const heads = [...document.querySelectorAll('main table thead th')].map(t => t.innerText.trim());
  return [...document.querySelectorAll('main table tbody tr')].map(tr => {
    const cells = [...tr.querySelectorAll('td')];
    const row = {};
    for (let i = 1; i <= cells.length && i <= heads.length; i++) {
      const h = heads[heads.length - i];
      if (h) row[h] = cells[cells.length - i].innerText.replace(/\\s+/g, ' ').trim();
    }
    const img = tr.querySelector('img');
    if (img) row._image = img.src;
    const link = tr.querySelector('a[href^="/"]');
    if (link) row._link = link.getAttribute('href');
    return row;
  });
}"""


def _ctx(pw, headless):
    return pw.chromium.launch_persistent_context(user_data_dir=PROFILE_DIR, headless=headless, viewport={"width": 1500, "height": 1000})


def _money(s):
    m = re.search(r"£\s?([\d,]+(?:\.\d+)?)", s or "")
    return float(m.group(1).replace(",", "")) if m else None


def _num(pattern, text, cast=int):
    m = re.search(pattern, text)
    if not m:
        return None
    v = m.group(1).replace(",", "").replace("£", "")
    try:
        return cast(v)
    except ValueError:
        return None


def _days(s):
    m = re.search(r"(-?\d+)\s*d\b", s or "")
    return int(m.group(1)) if m else None


def _open(page, path, wait_table=True, ready=None):
    """Load a page and wait until its real data (not loading skeletons) is on screen."""
    page.goto(BASE + path, wait_until="domcontentloaded", timeout=60000)
    if ready:
        try:
            page.wait_for_function("re => new RegExp(re).test(document.querySelector('main')?.innerText || '')", arg=ready, timeout=30000)
        except Exception:
            pass
    if wait_table:
        try:
            page.wait_for_function("""() => { const r = document.querySelectorAll('main table tbody tr');
                return r.length === 0 || [...r].some(tr => tr.innerText.trim().length > 3); }""", timeout=20000)
        except Exception:
            pass
    page.wait_for_timeout(1500)
    return page.inner_text("main")


def _is_logged_in(page):
    return "/dashboard" in page.url and "Welcome back" in (page.inner_text("main") if page.query_selector("main") else "")


def login():
    with sync_playwright() as pw:
        ctx = _ctx(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE + "/dashboard")
        print("Log in to ReclaimHQ in the window that opened. It will close by itself once you're in.")
        for _ in range(600):
            page.wait_for_timeout(1000)
            try:
                if _is_logged_in(page):
                    print("Logged in — session saved.")
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass
        ctx.close()


def _parse_dashboard(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    def after(label, n=1):
        try:
            i = lines.index(label)
            return lines[i + n]
        except (ValueError, IndexError):
            return None

    radar = []
    try:
        i = lines.index("Deadline Radar")
        j = lines.index("Leak Detector", i)
        block = [l for l in lines[i + 1:j] if l != "View all" and "need action" not in l]
        for k in range(0, len(block) - 3, 4):
            title, asin, value, days = block[k:k + 4]
            radar.append({"title": title, "asin": asin, "value": _money(value), "days": _days(days)})
    except ValueError:
        pass
    synced = next((l.replace("Last synced:", "").strip() for l in lines if l.startswith("Last synced")), None)
    leak_note = after("Leak Detector", 2) or ""
    return {
        "recovered30": _money(after("Recovered (30d)")),
        "atRisk14": _money(after("At risk (14d)")),
        "atRiskNote": after("At risk (14d)", 2),
        "openOrders": _num(r"(\d+)", after("Open orders") or ""),
        "radar": radar,
        "radarNote": next((l for l in lines if "need action" in l), None),
        "leakShortfall": _money(after("Leak Detector")),
        "leakNote": leak_note,
        "expiredWinnable": _money(leak_note.split("+")[-1]) if "+" in leak_note else None,
        "recoveredAllTime": _num(r"£([\d,]+\.\d+) recovered all time", text, float),
        "nextAction": after("Next action"),
        "lastSynced": synced,
    }


def build():
    if not Path(PROFILE_DIR).exists():
        return {"configured": False, "needsLogin": True}
    with sync_playwright() as pw:
        ctx = _ctx(pw, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            dash_text = _open(page, "/dashboard", ready=r"Recovered \(30d\)\s+£")
            if not _is_logged_in(page):
                return {"configured": False, "needsLogin": True}

            claims_text = _open(page, "/claims", ready=r"All Claims\s+\d+")
            claim_rows = page.evaluate(TABLE_JS)
            leak_text = _open(page, "/leak-detector", ready=r"Total Leaks\s+\d+")
            leak_rows = page.evaluate(TABLE_JS)
            orders_text = _open(page, "/orders?expiring=14", ready=r"Total Orders\s+\d+")
            order_rows = page.evaluate(TABLE_JS)
        finally:
            ctx.close()

    claims = []
    for r in claim_rows:
        if not (r.get("Product") or r.get("Status")):
            continue
        product = r.get("Product", "")
        claims.append({
            "product": product[:120], "order": r.get("Order"), "status": r.get("Status"), "caseId": r.get("Detail"),
            "expiry": r.get("Expiry") if r.get("Expiry") not in ("", "-") else None, "expiryDays": _days(r.get("Expiry")),
            "value": r.get("Value"), "image": r.get("_image"),
        })
    leaks = []
    for r in leak_rows:
        if not (r.get("Reimbursement ID") or r.get("Product")):
            continue
        rid_date = (r.get("Reimbursement ID") or "").split(" ", 1)
        leaks.append({
            "reimbursementId": rid_date[0], "date": rid_date[1] if len(rid_date) > 1 else None,
            "product": (r.get("Product") or "")[:120], "reimbursed": _money(r.get("Reimbursed")), "cog": _money(r.get("COG (ex VAT)")),
            "shortfall": _money(r.get("Shortfall")), "expiresDays": _days(r.get("Expires")), "status": r.get("Status"),
            "caseId": r.get("Case ID") or None, "image": r.get("_image"),
        })
    leaks.sort(key=lambda x: (x["expiresDays"] if x["expiresDays"] is not None else 999))
    expiring = []
    for r in order_rows:
        oid = (r.get("Removal Order ID") or "").split(" ", 1)
        expiring.append({
            "orderId": oid[0], "detail": oid[1] if len(oid) > 1 else "", "status": r.get("Status"),
            "cases": _num(r"(\d+)", r.get("Cases") or ""), "deadlineDays": _days(r.get("Filing deadline")),
            "created": r.get("Created"), "link": r.get("_link"),
        })
    expiring.sort(key=lambda x: (x["deadlineDays"] if x["deadlineDays"] is not None else 999))

    return {
        "configured": True,
        "updated": uk_now().strftime("%H:%M"),
        "errors": [],
        "dashboard": _parse_dashboard(dash_text),
        "claimCounts": {
            "all": _num(r"All Claims\s+(\d+)", claims_text), "actionRequired": _num(r"Action Required\s+(\d+)", claims_text),
            "active": _num(r"Active\s+(\d+)", claims_text), "won": _num(r"Won\s+(\d+)", claims_text),
            "lost": _num(r"Lost\s+(\d+)", claims_text), "recovered": _num(r"Recovered\s+£([\d,]+\.?\d*)", claims_text, float),
        },
        "claims": claims,
        "leakStats": {
            "total": _num(r"Total Leaks\s+(\d+)", leak_text), "shortfall": _num(r"Total Shortfall\s+£([\d,]+\.?\d*)", leak_text, float),
            "openCases": _num(r"Open Cases\s+(\d+)", leak_text), "recovered": _num(r"Recovered\s+£([\d,]+\.?\d*)\s+Shortfall recovered", leak_text, float),
        },
        "leaks": leaks,
        "ordersStats": {
            "totalOrders": _num(r"Total Orders\s+(\d+)", orders_text), "totalItems": _num(r"Total Items\s+(\d+)", orders_text),
            "activeClaims": _num(r"Active Claims\s+(\d+)", orders_text), "atRisk": _num(r"At Risk\s+£([\d,]+\.?\d*)", orders_text, float),
        },
        "expiring": expiring,
    }


if __name__ == "__main__":
    if "--login" in sys.argv:
        login()
    else:
        print(json.dumps(build(), indent=2, ensure_ascii=False)[:5000])
