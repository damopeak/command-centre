"""Command Centre - local dashboard server.

Serves the app from ./app at http://127.0.0.1:8765
    /api/health   server is up
    /api/fba      Invenno profit figures (cached, refreshed every 15 minutes)
    /api/fba/range?from=YYYY-MM-DD&to=YYYY-MM-DD   live figures for any date range
    /api/isa      Vanguard ISA valued at live prices (refreshed every 10 minutes)
    POST /api/isa/holdings   save edited units / average cost / cash
    /api/monitors deal monitor status + leads from oa-bot logs (every 2 minutes)
    POST /api/monitors/start?id=argos   relaunch a stopped monitor via its Startup shortcut
    /api/otp      delivery codes (Amazon/DPD OTPs) -> dashboard + your Discord webhook (every 90 seconds)
    /api/important important emails from Gmail (IMAP, read-only, every 10 minutes)
    /api/calendar Google Calendar via secret iCal addresses (every 10 minutes)
    /api/jobs     job scraper matches + application tracker (refreshed every 15 minutes)
    /api/reclaim  ReclaimHQ claims, deadlines and leaks (refreshed every 30 minutes)
"""
import json
from datetime import datetime
import mimetypes
import sys
import threading
import time
import traceback
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import invenno
import reclaim
import jobs
import isa
import monitors
import calendar_feed
import important
import otp_watch
import chat
import purchases
import bank
import stock
import insights
import deadlines
import urgent

mimetypes.add_type("application/manifest+json", ".webmanifest")

HOST, PORT = "127.0.0.1", 8765
ROOT = Path(__file__).parent
APP_DIR = ROOT / "app"
FBA_REFRESH_SECONDS = 15 * 60
RECLAIM_REFRESH_SECONDS = 30 * 60

class StampedCache(dict):
    """Remembers when each data source last finished a check (for the dashboard's system HUD)."""
    checked = {}

    def __setitem__(self, key, value):
        StampedCache.checked[key] = time.strftime("%Y-%m-%dT%H:%M:%S")
        super().__setitem__(key, value)


STARTED = time.strftime("%Y-%m-%dT%H:%M:%S")
cache = StampedCache({"fba": {"configured": None, "loading": True}, "reclaim": {"configured": None, "loading": True},
         "jobs": {"configured": None, "loading": True},
         "isa": {"configured": None, "loading": True},
         "monitors": {"configured": None, "loading": True},
         "calendar": {"configured": None, "loading": True},
         "important": {"configured": None, "loading": True},
         "otp": {"configured": None, "loading": True},
         "purchases": {"configured": None, "loading": True}})
cache_lock = threading.Lock()
refresh_now = threading.Event()
refresh_reclaim = threading.Event()
refresh_jobs = threading.Event()
refresh_isa = threading.Event()
refresh_monitors = threading.Event()
refresh_calendar = threading.Event()
refresh_important = threading.Event()
refresh_otp = threading.Event()


def log(msg):
    with (ROOT / "server.log").open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def fba_worker():
    while True:
        try:
            data = invenno.build_fba()
        except Exception as e:  # keep the dashboard alive whatever Amazon returns
            log("FBA refresh failed:\n" + traceback.format_exc())
            data = {"configured": True, "errors": [f"Refresh failed: {e}"]}
        last = ROOT / "fba_last.json"
        if data.get("sales30"):
            last.write_text(json.dumps(data), encoding="utf-8")
        elif data.get("needsLogin") and last.exists():
            # Login expired: keep showing the last real figures, flagged as stale
            data = {**json.loads(last.read_text(encoding="utf-8")), "needsLogin": True, "stale": True}
        with cache_lock:
            cache["fba"] = data
        for err in data.get("errors", []):
            log("FBA: " + err)
        refresh_now.wait(FBA_REFRESH_SECONDS)
        refresh_now.clear()


def reclaim_worker():
    while True:
        try:
            data = reclaim.build()
        except Exception as e:
            log("ReclaimHQ refresh failed:\n" + traceback.format_exc())
            with cache_lock:
                old = cache["reclaim"]
            data = dict(old) if old.get("configured") else {"configured": True}
            data["errors"] = [f"ReclaimHQ refresh failed: {e}"]
        with cache_lock:
            cache["reclaim"] = data
        refresh_reclaim.wait(RECLAIM_REFRESH_SECONDS)
        refresh_reclaim.clear()


refresh_purchases = threading.Event()


refresh_bank = threading.Event()
refresh_stock = threading.Event()
refresh_deadlines = threading.Event()


def deadlines_worker():
    time.sleep(300)  # let the other mail workers go first after a restart
    while True:
        try:
            if deadlines._load().get("enabled"):   # switched on after the v6 sheet script is deployed and tested
                deadlines.run()
        except Exception:
            log("Deadlines -> calendar failed:" + chr(10) + traceback.format_exc())
        refresh_deadlines.wait(30 * 60)
        refresh_deadlines.clear()
stock_cache = {"loading": True}


def stock_worker():
    global stock_cache
    time.sleep(240)  # after the FBA and purchases workers have used the Invenno profile
    while True:
        try:
            stock_cache = stock.build()
        except Exception as e:
            log("Stock ageing failed:" + chr(10) + traceback.format_exc())
            stock_cache = {**{k: v for k, v in stock_cache.items() if k != "loading"}, "error": str(e)}
        refresh_stock.wait(6 * 3600)
        refresh_stock.clear()


def bank_worker():
    while True:
        try:
            if bank._cfg()["ok"] and bank._load()["connections"]:
                data = bank.sync()
                for e in data.get("errors", []):
                    log("Bank: " + e)
        except Exception:
            log("Bank sync failed:" + chr(10) + traceback.format_exc())
        refresh_bank.wait(6 * 3600)
        refresh_bank.clear()


def purchases_worker():
    time.sleep(90)  # let the FBA worker use the Invenno profile first after a restart
    while True:
        try:
            data = purchases.build()
            if data.get("posted"):
                log(f"Purchases: posted {data['posted']} alert(s) to Discord")
        except Exception as e:
            log("Purchases refresh failed:" + chr(10) + traceback.format_exc())
            with cache_lock:
                old = cache["purchases"]
            data = dict(old) if old.get("cards") else {"configured": True, "cards": [], "summary": {}}
            data["errors"] = [f"Purchases refresh failed: {e}"]
        with cache_lock:
            cache["purchases"] = data
        refresh_purchases.wait(20 * 60)
        refresh_purchases.clear()


def otp_worker():
    while True:
        try:
            data = otp_watch.build()
            for code in data.get("postedNow", []):
                log(f"OTP posted to Discord ({len(code)} digits)")
        except Exception as e:
            log("OTP check failed:" + chr(10) + traceback.format_exc())
            with cache_lock:
                old = cache["otp"]
            data = dict(old) if old.get("configured") else {"configured": True, "codes": []}
            data["errors"] = [f"Delivery code check failed: {e}"]
        with cache_lock:
            cache["otp"] = data
        refresh_otp.wait(90)
        refresh_otp.clear()


def important_worker():
    while True:
        try:
            data = important.build()
        except Exception as e:
            log("Important refresh failed:" + chr(10) + traceback.format_exc())
            data = {"configured": True, "errors": [f"Email check failed: {e}"], "items": []}
        with cache_lock:
            cache["important"] = data
        try:
            for t in urgent.check(important_data=data, deadline_events=list(deadlines._load().get("events", {}).values())):
                log("Urgent alert: " + t)
        except Exception:
            log("Urgent alert failed:" + chr(10) + traceback.format_exc())
        refresh_important.wait(10 * 60)
        refresh_important.clear()


def calendar_worker():
    while True:
        try:
            data = calendar_feed.build()
        except Exception as e:
            log("Calendar refresh failed:" + chr(10) + traceback.format_exc())
            data = {"configured": True, "errors": [f"Calendar refresh failed: {e}"], "events": []}
        with cache_lock:
            cache["calendar"] = data
        refresh_calendar.wait(10 * 60)
        refresh_calendar.clear()


def monitors_worker():
    while True:
        try:
            data = monitors.build()
        except Exception as e:
            log("Monitors refresh failed:" + chr(10) + traceback.format_exc())
            data = {"configured": True, "errors": [f"Monitor read failed: {e}"], "monitors": [], "leads": []}
        with cache_lock:
            cache["monitors"] = data
        refresh_monitors.wait(2 * 60)
        refresh_monitors.clear()


def isa_worker():
    while True:
        try:
            data = isa.build()
        except Exception as e:
            log("ISA refresh failed:" + chr(10) + traceback.format_exc())
            with cache_lock:
                old = cache["isa"]
            data = dict(old) if old.get("configured") else {"configured": True}
            data["errors"] = [f"ISA price refresh failed: {e}"]
        with cache_lock:
            cache["isa"] = data
        refresh_isa.wait(10 * 60)
        refresh_isa.clear()


def jobs_worker():
    while True:
        try:
            data = jobs.build()
        except Exception as e:
            log("Jobs refresh failed:\n" + traceback.format_exc())
            with cache_lock:
                old = cache["jobs"]
            data = dict(old) if old.get("configured") else {"configured": True}
            data["errors"] = [f"Job dashboard refresh failed: {e}"]
        with cache_lock:
            cache["jobs"] = data
        refresh_jobs.wait(15 * 60)
        refresh_jobs.clear()


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            with cache_lock:
                errs = {k: bool(v.get("errors") or v.get("needsLogin")) for k, v in cache.items() if isinstance(v, dict)}
            return self.send_json({"status": "ok", "started": STARTED, "checked": StampedCache.checked, "errors": errs})
        if self.path.startswith("/api/isa/holdings"):
            return self.send_json(isa.load_holdings())
        if self.path.startswith("/api/bank/connect"):
            host = self.headers.get("Host", "127.0.0.1:8765")
            base = "http://localhost:8765" if host.startswith(("127.0.0.1", "localhost")) else "https://" + host.split(":")[0]
            self.send_response(302)
            self.send_header("Location", bank.connect_url(base + "/api/bank/callback"))
            self.end_headers()
            return
        if self.path.startswith("/api/bank/callback"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            if "error" in q:
                msg = "Bank connection cancelled: " + q["error"][0]
            else:
                try:
                    conn = bank.callback(q["code"][0], q.get("state", [""])[0])
                    msg = "Connected " + conn["provider"]
                    refresh_bank.set()
                except Exception as e:
                    log("Bank callback failed:" + chr(10) + traceback.format_exc())
                    msg = "Bank connection failed: " + str(e)
            from urllib.parse import quote
            self.send_response(302)
            self.send_header("Location", "/#money?msg=" + quote(msg))
            self.end_headers()
            return
        if self.path.startswith("/api/deadlines"):
            if "refresh=1" in self.path:
                refresh_deadlines.set()
            return self.send_json(deadlines.summary())
        if self.path.startswith("/api/insights"):
            import copy
            import ledger
            if "refresh=1" in self.path:
                refresh_stock.set()
            with cache_lock:
                cards = copy.deepcopy(cache["purchases"].get("cards") or [])
                fba = dict(cache["fba"])
            txns, _ = bank.ledger_transactions()
            L = ledger.build({"transactions": txns}, copy.deepcopy(cards))
            ch = insights.chaser(cards)
            raw, _ = bank.load_csv()
            return self.send_json({"chaser": ch, "digest": insights.digest(cards, L, fba, ch), "cashflow": insights.cashflow(L, raw, fba),
                                   "stock": stock_cache, "notLive": [
                                       {k: c.get(k) for k in ("source", "title", "qty", "stage", "orderedAt", "dest", "total", "currency")}
                                       for c in cards if not c.get("cancelled") and c.get("stage") in ("ordered", "shipped", "delivered", "atprep", "prepped")
                                       and (datetime.now() - datetime.fromisoformat(c["orderedAt"][:16])).days > stock.NOT_LIVE_DAYS]})
        if self.path.startswith("/api/money"):
            import copy
            import ledger
            with cache_lock:
                cards = copy.deepcopy(cache["purchases"].get("cards") or [])
            txns, files = bank.ledger_transactions()
            L = ledger.build({"transactions": txns}, cards)
            live = bank.cached()
            L.update({"files": files, "sandbox": live.get("sandbox"), "connections": live.get("connections") or [],
                      "testSources": len(live.get("sources") or []) if live.get("sandbox") else 0})
            return self.send_json(L)
        if self.path.startswith("/api/bank"):
            if "refresh=1" in self.path:
                refresh_bank.set()
            return self.send_json(bank.cached())
        if self.path.startswith("/api/purchases"):
            if "refresh=1" in self.path:
                refresh_purchases.set()
            with cache_lock:
                return self.send_json(cache["purchases"])
        if self.path.startswith("/api/otp"):
            if "refresh=1" in self.path:
                refresh_otp.set()
            with cache_lock:
                return self.send_json(cache["otp"])
        if self.path.startswith("/api/important"):
            if "refresh=1" in self.path:
                refresh_important.set()
            with cache_lock:
                data = cache["important"]
            return self.send_json(urgent.apply_done(data) if data.get("items") else data)
        if self.path.startswith("/api/calendar"):
            if "refresh=1" in self.path:
                refresh_calendar.set()
            with cache_lock:
                return self.send_json(cache["calendar"])
        if self.path.startswith("/api/monitors"):
            if "refresh=1" in self.path:
                refresh_monitors.set()
            with cache_lock:
                return self.send_json(cache["monitors"])
        if self.path.startswith("/api/isa"):
            if "refresh=1" in self.path:
                refresh_isa.set()
            with cache_lock:
                return self.send_json(cache["isa"])
        if self.path.startswith("/api/jobs"):
            if "refresh=1" in self.path:
                refresh_jobs.set()
            with cache_lock:
                return self.send_json(cache["jobs"])
        if self.path.startswith("/api/reclaim"):
            if "refresh=1" in self.path:
                refresh_reclaim.set()
            with cache_lock:
                return self.send_json(cache["reclaim"])
        if self.path.startswith("/api/fba/range"):
            from urllib.parse import parse_qs, urlparse
            from datetime import date
            qs = parse_qs(urlparse(self.path).query)
            try:
                frm, to = date.fromisoformat(qs["from"][0]), date.fromisoformat(qs["to"][0])
                return self.send_json(invenno.range_data(frm, to))
            except invenno.NeedsLogin:
                return self.send_json({"error": "Invenno session expired. Double-click connect-invenno.bat to log in again.", "needsLogin": True})
            except Exception as e:
                log("Range query failed:\n" + traceback.format_exc())
                return self.send_json({"error": f"Couldn't load that range: {e}"})
        if self.path.startswith("/api/fba"):
            if "refresh=1" in self.path:
                refresh_now.set()
            with cache_lock:
                return self.send_json(cache["fba"])
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/insights/chase"):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                return self.send_json({"ok": True, **insights.chase_action(body["key"], body["action"])})
            except Exception as e:
                return self.send_json({"ok": False, "error": str(e)})
        if self.path.startswith("/api/important/done"):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if body.get("restore"):
                urgent.restore_done()
            else:
                urgent.mark_done(str(body.get("id", "")), str(body.get("groupKey", "")))
            return self.send_json({"ok": True})
        if self.path.startswith("/api/money/answer"):
            try:
                import ledger
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if body.get("category") not in ledger.CATEGORIES:
                    raise ValueError("unknown category")
                ledger.answer(body["id"], body["category"], body.get("merchantKey"), body.get("remember", True))
                return self.send_json({"ok": True})
            except Exception as e:
                return self.send_json({"ok": False, "error": str(e)})
        if self.path.startswith("/api/purchases/note"):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                saved = purchases.set_note(body["key"], body.get("text", ""))
                with cache_lock:
                    for c in cache["purchases"].get("cards") or []:
                        if c["id"] == body["key"]:
                            c["userNote"], c["userNoteAt"] = saved["text"], saved["at"]
                return self.send_json({"ok": True, **saved})
            except Exception as e:
                return self.send_json({"ok": False, "error": str(e)})
        if self.path.startswith("/api/chat"):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path.startswith("/api/chat/undo"):
                    return self.send_json(chat.undo(body.get("backup")))
                msgs = body.get("messages") or []
                if body.get("mode") == "edit":
                    return self.send_json(chat.edit(msgs))
                with cache_lock:
                    snap = dict(cache)
                return self.send_json(chat.ask(msgs, snap))
            except Exception as e:
                log("Chat failed:" + chr(10) + traceback.format_exc())
                return self.send_json({"ok": False, "error": str(e)})
        if self.path.startswith("/api/leads/status"):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                res = monitors.set_status(body["key"], body.get("status"), body.get("lead"))
                refresh_monitors.set()
                return self.send_json(res)
            except Exception as e:
                return self.send_json({"ok": False, "error": str(e)})
        if self.path.startswith("/api/monitors/start"):
            from urllib.parse import parse_qs, urlparse
            mid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            res = monitors.start(mid)
            refresh_monitors.set()
            return self.send_json(res)
        if self.path.startswith("/api/isa/holdings"):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                cfg = isa.load_holdings()
                by_ticker = {h["ticker"]: h for h in cfg["holdings"]}
                for h in body.get("holdings", []):
                    if h.get("ticker") in by_ticker:
                        by_ticker[h["ticker"]]["units"] = float(h["units"])
                        by_ticker[h["ticker"]]["totalCost"] = float(h["totalCost"])
                        by_ticker[h["ticker"]].pop("avgCost", None)
                if "cash" in body:
                    cfg["cash"] = float(body["cash"])
                if body.get("netContributions") is not None:
                    cfg["netContributions"] = float(body["netContributions"])
                cfg["asOf"] = time.strftime("%Y-%m-%d")
                isa.save_holdings(cfg)
                data = isa.build()
                with cache_lock:
                    cache["isa"] = data
                return self.send_json({"ok": True, "isa": data})
            except Exception as e:
                log("Holdings save failed:" + chr(10) + traceback.format_exc())
                return self.send_json({"ok": False, "error": str(e)})
        self.send_error(404)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=fba_worker, daemon=True).start()
    threading.Thread(target=reclaim_worker, daemon=True).start()
    threading.Thread(target=jobs_worker, daemon=True).start()
    threading.Thread(target=isa_worker, daemon=True).start()
    threading.Thread(target=monitors_worker, daemon=True).start()
    threading.Thread(target=calendar_worker, daemon=True).start()
    threading.Thread(target=important_worker, daemon=True).start()
    threading.Thread(target=otp_worker, daemon=True).start()
    threading.Thread(target=purchases_worker, daemon=True).start()
    threading.Thread(target=bank_worker, daemon=True).start()
    threading.Thread(target=stock_worker, daemon=True).start()
    threading.Thread(target=deadlines_worker, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), partial(Handler, directory=str(APP_DIR)))
    url = f"http://{HOST}:{PORT}/"
    print(f"Command Centre running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
