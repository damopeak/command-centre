"""Deal monitors connector: status + leads from the oa-bot services' logs and state files.

Reads (never writes) the oa-bot folder (OA_BOT_DIR in .env). Can start a stopped service via its Startup shortcut.
Test:  python monitors.py
"""
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from spapi import load_env, uk_now

OA = Path(load_env().get("OA_BOT_DIR") or Path(__file__).parent.parent / "oa-bot")
STARTUP = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"

MONITORS = [
    # Argos / TK Maxx (ArbiSource) and Currys removed at the user's request, 11 Oct 2026
    {"id": "hukd", "name": "HUKD hot deals", "store": "HUKD", "script": "hukd_monitor.py", "log": "hukd_monitor.log",
     "kind": "hukd", "lnk": "HUKD Monitor.lnk", "staleMin": 20, "desc": "Every 5 min · deals turning HOT, resale filter"},
    {"id": "dbh", "name": "DBH Deals", "store": "DBH", "script": "dbh_leads_monitor.py", "log": "dbh_leads_monitor.log",
     "kind": "dbh", "lnk": "DBH Deals Notifier.lnk", "staleMin": 20, "desc": "New leads on dbhdeals.com/leads"},
]

TS = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})")
ARBI = re.compile(r"DEAL \[(\w+) (\d+)\] (.+?) \| £([\d.]+) -> £([\d.]+) \| £(-?[\d.]+) (-?\d+)% \| (.+)$")
CURRYS = re.compile(r"DEAL '(.+?)' \| (new|£[\d.]+ -> £[\d.]+) \| ROI (-?[\d.]+)% \| £(-?[\d.]+) \| (.+)$")
HUKD = re.compile(r"INFO post\s+(\d+) (.+?)\s+— £([\d.,]+) @ (.+)$")
DBH = re.compile(r"(\d+) new deal\(s\) posted: (.+)$")


def _tail_lines(path, max_bytes=3_000_000):
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            f.seek(max(0, size - max_bytes))
            data = f.read().decode("utf-8", "ignore")
        return data.splitlines()
    except FileNotFoundError:
        return []


def _ts(line):
    m = TS.match(line)
    return datetime.fromisoformat(f"{m.group(1)} {m.group(2)}") if m else None


def running_scripts():
    """Script names of oa-bot Python processes currently running."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | ForEach-Object { $_.CommandLine }"],
            capture_output=True, text=True, timeout=20, creationflags=0x08000000).stdout
    except Exception:
        return set()
    return {m["script"] for m in MONITORS if m["script"] in out}


def _asin_lookup(state_file):
    """alerted ASINs by (price, epoch) so log lines can be linked to Amazon."""
    try:
        alerted = json.loads((OA / state_file).read_text(encoding="utf-8")).get("alerted", {})
    except Exception:
        return []
    return [(asin, float(v.get("price", 0)), float(v.get("at", 0))) for asin, v in alerted.items()]


def _money(v):
    m = re.search(r"-?[\d,]+(?:\.\d+)?", str(v or "").replace("£", ""))
    return float(m.group(0).replace(",", "")) if m else None


def dbh_posted():
    """Deals the DBH notifier posted, each with its own dbhdeals.com/leads/<id> page."""
    try:
        rows = json.loads((OA / "dbh_posted.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    leads = []
    for d in rows:
        try:
            t = datetime.fromisoformat(d["posted_at"])
        except Exception:
            continue
        leads.append({"t": t, "title": d.get("title") or "DBH deal", "buy": _money(d.get("buy")), "sell": _money(d.get("sell")),
                      "profit": _money(d.get("profit")), "roi": round(_money(d.get("roi"))) if _money(d.get("roi")) is not None else None,
                      "tag": d.get("store") or d.get("buy_label") or "new lead", "via": "DBH",
                      "url": d.get("url"), "asin": d.get("asin"), "buyUrl": d.get("buy_url")})
    return leads


def parse(mon):
    lines = _tail_lines(OA / mon["log"])
    leads, warnings, last_ts, last_event = [], 0, None, ""
    day_ago = datetime.now() - timedelta(hours=24)
    asins = _asin_lookup(mon["state"]) if mon.get("state") else []
    posted = dbh_posted() if mon["kind"] == "dbh" else None
    if posted is not None:
        leads.extend(posted)
    for line in lines:
        t = _ts(line)
        if t:
            last_ts = t
        if not t:
            continue
        if (" WARNING " in line or " ERROR " in line or "[ERROR]" in line or "[WARNING]" in line) and t >= day_ago:
            warnings += 1
        k = mon["kind"]
        if k == "arbi":
            if "finished:" in line or "started full" in line or "Service started" in line:
                last_event = line[24:].replace("INFO ", "").strip()
            m = ARBI.search(line)
            if m:
                tier, score, title, buy, sell, profit, roi, via = m.groups()
                asin = None
                for a, price, at in asins:
                    if abs(price - float(buy)) < 0.01 and abs(at - t.timestamp()) < 120:
                        asin = a
                        break
                leads.append({"t": t, "title": title.strip(), "buy": float(buy), "sell": float(sell), "profit": float(profit),
                              "roi": int(roi), "tag": f"{tier} {score}", "via": via.strip(),
                              "url": f"https://www.amazon.co.uk/dp/{asin}" if asin else None})
        elif k == "currys":
            if "Cycle done" in line:
                last_event = line[20:].replace("[INFO] ", "").strip()
            m = CURRYS.search(line)
            if m:
                title, kind, roi, profit, via = m.groups()
                was = now_price = None
                if kind != "new":
                    was, now_price = (float(x) for x in re.findall(r"£([\d.]+)", kind))
                leads.append({"t": t, "title": title, "buy": now_price, "was": was, "sell": None, "profit": float(profit),
                              "roi": round(float(roi)), "tag": "price drop" if was else "new line", "via": via.strip(), "url": None})
        elif k == "hukd":
            m = HUKD.search(line)
            if m:
                did, title, price, shop = m.groups()
                leads.append({"t": t, "title": title.strip(), "buy": float(price.replace(",", "")), "sell": None, "profit": None,
                              "roi": None, "tag": shop.strip(), "via": "hot deal",
                              "url": f"https://www.hotukdeals.com/deals/x-{did}"})
            if " post " in line or " skip " in line:
                last_event = "checked HUKD"
        elif k == "dbh":
            if "No new deals" in line or "posted" in line:
                last_event = "checked dbhdeals.com/leads"
            m = DBH.search(line) if posted is None else None
            if m:
                for title in m.group(2).split("; "):
                    leads.append({"t": t, "title": title.replace("&quot", '"').strip(), "buy": None, "sell": None, "profit": None,
                                  "roi": None, "tag": "new lead", "via": "DBH", "url": "https://www.dbhdeals.com/leads"})
    return leads, warnings, last_ts, last_event


DISCORD_FILE = Path(__file__).parent / "discord_leads.json"


def discord_source():
    """Leads picked from Discord monitor channels during on-demand checks (no automation of the Discord account)."""
    try:
        d = json.loads(DISCORD_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None, []
    leads = []
    for l in d.get("leads", []):
        try:
            t = datetime.fromisoformat(l["time"])
        except Exception:
            continue
        leads.append({"t": t, "title": l.get("title", ""), "buy": l.get("buy"), "sell": l.get("sell"), "profit": l.get("profit"),
                      "roi": l.get("roi"), "tag": l.get("channel", "Discord"), "via": l.get("why", ""),
                      "url": l.get("url") or (f"https://www.amazon.co.uk/dp/{l['asin']}" if l.get("asin") else None),
                      "spm": l.get("spm"), "store": l.get("store"), "asin": l.get("asin"),
                      "supplierUrl": l.get("supplierUrl"), "sasUrl": l.get("sasUrl"), "discordUrl": l.get("discordUrl"),
                      "keepa": l.get("keepa"), "postedAt": l.get("postedAt") or l.get("time"), "channel": l.get("channel"),
                      "topPick": bool(l.get("topPick")), "pickWhy": l.get("pickWhy")})
    return d, leads


def build():
    now = datetime.now()
    today = now.date()
    week_ago = today - timedelta(days=6)
    running = running_scripts()
    monitors, all_leads = [], []
    for mon in MONITORS:
        leads, warnings, last_ts, last_event = parse(mon)
        is_running = mon["script"] in running
        age_min = (now - last_ts).total_seconds() / 60 if last_ts else None
        status = "err" if not is_running else ("warn" if age_min is None or age_min > mon["staleMin"] else "ok")
        today_leads = [l for l in leads if l["t"].date() == today]
        week_leads = [l for l in leads if l["t"].date() >= week_ago]
        rois = [l["roi"] for l in week_leads if l["roi"] is not None]
        profits = [l["profit"] for l in week_leads if l["profit"] is not None]
        monitors.append({
            "id": mon["id"], "name": mon["name"], "store": mon["store"], "desc": mon["desc"], "status": status,
            "running": is_running, "canStart": bool(mon["lnk"]) and not is_running,
            "lastActivity": last_ts.isoformat() if last_ts else None, "lastActivityMin": round(age_min) if age_min is not None else None,
            "lastEvent": last_event[:120], "warnings24h": warnings,
            "leadsToday": len(today_leads), "leadsWeek": len(week_leads),
            "medianRoi": sorted(rois)[len(rois) // 2] if rois else None,  # median: bad Keepa matches can show 10,000%
            "bestProfit": max(profits) if profits else None,
            "lastLead": leads[-1]["t"].isoformat() if leads else None,
        })
        for l in leads:
            all_leads.append({**l, "source": mon["store"], "monitor": mon["id"]})

    # Discord picks (on-demand checks)
    ddata, dleads = discord_source()
    if ddata is not None:
        last = ddata.get("lastCheck")
        last_dt = datetime.fromisoformat(last) if last else None
        week = [l for l in dleads if l["t"].date() >= week_ago]
        rois = [l["roi"] for l in week if l["roi"] is not None]
        monitors.append({
            "id": "discord", "name": "Discord picks", "store": "Discord", "manual": True,
            "desc": "On-demand checks of " + (", ".join("#" + c for c in ddata.get("checkedChannels", [])) or "your Discord monitor channels"),
            "status": "ok" if last_dt and (now - last_dt).total_seconds() < 86400 else "idle",
            "running": True, "canStart": False,
            "lastActivity": last_dt.isoformat() if last_dt else None,
            "lastActivityMin": round((now - last_dt).total_seconds() / 60) if last_dt else None,
            "lastEvent": "ask Claude: “check my Discord leads”", "warnings24h": 0,
            "leadsToday": sum(1 for l in dleads if l["t"].date() == today), "leadsWeek": len(week),
            "medianRoi": sorted(rois)[len(rois) // 2] if rois else None, "bestProfit": max((l["profit"] for l in week if l["profit"] is not None), default=None),
            "lastLead": max((l["t"] for l in dleads), default=None).isoformat() if dleads else None,
        })
        for l in dleads:
            all_leads.append({**l, "source": "Discord", "monitor": "discord"})

    all_leads.sort(key=lambda l: l["t"], reverse=True)
    days = [today - timedelta(days=n) for n in range(6, -1, -1)]
    stores = [m["store"] for m in MONITORS] + (["Discord"] if ddata is not None else [])
    per_day = {st: [sum(1 for l in all_leads if l["source"] == st and l["t"].date() == d) for d in days] for st in stores}
    out_leads = []
    # keep every profit-checked lead from the last 14 days, plus the newest HUKD posts
    recent = [l for l in all_leads if l["source"] != "HUKD" and l["t"].date() >= today - timedelta(days=13)]
    recent += [l for l in all_leads if l["source"] == "HUKD"][:80]
    recent.sort(key=lambda l: l["t"], reverse=True)
    statuses = load_statuses()
    seen_keys = set()
    for l in recent:
        o = {k: v for k, v in l.items() if k != "t"}
        o["time"] = l["t"].isoformat()
        o["key"] = lead_key(l)
        if o["key"] in seen_keys:
            continue
        seen_keys.add(o["key"])
        st = statuses.get(o["key"])
        if st:
            o["status"], o["statusAt"] = st.get("status"), st.get("at")
        out_leads.append(o)
    # leads marked bought/declined/out of stock stay visible in their section even after they age out
    for k, st in statuses.items():
        if k not in seen_keys and st.get("lead"):
            out_leads.append({**st["lead"], "key": k, "status": st.get("status"), "statusAt": st.get("at")})
    return {
        "configured": True, "updated": uk_now().strftime("%H:%M"),
        "monitors": monitors, "leads": out_leads,
        "days": [d.strftime("%a") if d != today else "Today" for d in days], "perDay": per_day,
        "totals": {"today": sum(m["leadsToday"] for m in monitors), "week": sum(m["leadsWeek"] for m in monitors),
                   "running": sum(1 for m in monitors if m["running"] and not m.get("manual")),
                   "count": sum(1 for m in monitors if not m.get("manual"))},
    }


STATUS_FILE = Path(__file__).parent / "leads_status.json"
STATUSES = ("bought", "declined", "oos")


def lead_key(l):
    ident = l.get("asin") or l.get("url") or l.get("title", "")[:60]
    return f"{l.get('source', '')}|{ident}|{l['t'].date() if 't' in l else l.get('time', '')[:10]}"


def load_statuses():
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_status(key, status, lead=None):
    data = load_statuses()
    if status in STATUSES:
        data[key] = {"status": status, "at": datetime.now().isoformat(timespec="minutes"), "lead": lead}
    else:  # "active" / anything else -> back to the leads list
        data.pop(key, None)
    STATUS_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"ok": True}


def start(monitor_id):
    mon = next((m for m in MONITORS if m["id"] == monitor_id), None)
    if not mon or not mon["lnk"]:
        return {"ok": False, "error": "This monitor has no Startup shortcut to launch."}
    if mon["script"] in running_scripts():
        return {"ok": True, "already": True}
    os.startfile(str(STARTUP / mon["lnk"]))
    time.sleep(3)
    return {"ok": mon["script"] in running_scripts()}


if __name__ == "__main__":
    d = build()
    for m in d["monitors"]:
        print(m)
    print(d["totals"], d["perDay"])
    for l in d["leads"][:8]:
        print(l["time"][:16], l["source"], l["title"][:50], l["buy"], l["profit"], l["roi"], l["url"])
