"""Urgent alerts + shared "Done" state for the Important tab.

Urgent = a High-priority Important email (arrears notice, Amazon disposal warning, real security alert...) that arrived in
the last 2 days, or a calendar deadline/booking within the next 48 hours. Each one is announced once by:
  * a Windows popup (same toast as the Discord-leads reminder)
  * a post to URGENT_WEBHOOK_URL in .env (a private channel in the user's own Discord server), if set
The dashboard shows them as glowing red cards as before.

Done (13 Oct 2026, user's choice): clicking Done on an Important email hides it on every device and also hides repeats
of the same sender + subject for 7 days.
"""
import json
import threading
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from spapi import load_env

ROOT = Path(__file__).parent
STATE = ROOT / "urgent_state.json"
DONE = ROOT / "important_done.json"
REPEAT_DAYS = 7
_lock = threading.Lock()


def _read(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


# ---------- Done ----------
def mark_done(item_id, group_key):
    with _lock:
        d = _read(DONE, {"ids": {}, "groups": {}})
        now = datetime.now().isoformat(timespec="minutes")
        d["ids"][item_id] = now
        if group_key:
            d["groups"][group_key] = now
        cutoff = (datetime.now() - timedelta(days=60)).isoformat()
        d["ids"] = {k: v for k, v in d["ids"].items() if v > cutoff}
        DONE.write_text(json.dumps(d, indent=1), encoding="utf-8")


def restore_done():
    with _lock:
        DONE.write_text(json.dumps({"ids": {}, "groups": {}}), encoding="utf-8")


def apply_done(data):
    """Copy of the Important payload with done:true on items that are done (or repeats of a done one within 7 days)."""
    d = _read(DONE, {"ids": {}, "groups": {}})
    limit = (datetime.now() - timedelta(days=REPEAT_DAYS)).isoformat()
    out = dict(data)
    items = []
    for x in data.get("items", []):
        g = d["groups"].get(x.get("groupKey") or "")
        done = x["id"] in d["ids"] or bool(g and g > limit)
        items.append(dict(x, done=done))
    out["items"] = items
    return out


# ---------- Alerts ----------
def _toast(title, body):
    try:
        import discord_reminder
        discord_reminder.toast(title.replace("<", "").replace("&", "and"), body.replace("<", "").replace("&", "and"))
    except Exception:
        pass


def _discord(text):
    url = load_env().get("URGENT_WEBHOOK_URL", "").strip()
    if not url:
        return False
    req = urllib.request.Request(url, data=json.dumps({"content": text[:1900], "allowed_mentions": {"parse": []}}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "CommandCentre/1.0"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception:
        return False


def check(important_data=None, deadline_events=None):
    """Announce anything urgent that hasn't been announced yet. Safe to call often."""
    with _lock:
        st = _read(STATE, {"sent": {}})
        now = datetime.now()
        new = []
        if important_data:
            recent = (now - timedelta(days=2)).isoformat()
            for x in apply_done(important_data).get("items", []):
                if x.get("priority") == 1 and not x.get("done") and x.get("received", "") >= recent:
                    k = "mail:" + x["id"]
                    if k not in st["sent"]:
                        new.append((k, f"⚠️ {x['subject'][:80]}", f"{x['from']} · {x['account']} · {x['reason']}", x.get("url")))
        for e in deadline_events or []:
            try:
                start = datetime.fromisoformat(e["start"])
            except Exception:
                continue
            if now - timedelta(hours=12) <= start <= now + timedelta(hours=48):
                k = "deadline:" + e.get("key", e["title"] + e["start"])
                if k not in st["sent"]:
                    when = start.strftime("%a %d %b") + ("" if start.strftime("%H:%M") == "09:00" else start.strftime(" %H:%M"))
                    new.append((k, f"{e['title'][:80]}", f"Due {when} · {e.get('account', '')}", e.get("link")))
        for k, title, body, link in new:
            _toast(title, body)
            _discord(f"**{title}**\n{body}" + (f"\n<{link}>" if link else ""))
            st["sent"][k] = now.isoformat(timespec="minutes")
        cutoff = (now - timedelta(days=30)).isoformat()
        st["sent"] = {k: v for k, v in st["sent"].items() if v > cutoff}
        STATE.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
        return [t for _, t, _, _ in new]
