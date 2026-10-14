"""Delivery OTP watcher: finds Amazon / DPD (and other carrier) delivery codes in your inboxes,
shows them on the dashboard and posts them to YOUR OWN Discord channel via a webhook.

Uses the same read-only Gmail IMAP logins as the Important tab (GMAIL_1, GMAIL_2 in .env),
plus iCloud (ICLOUD_1=you@example.com|app-specific-password), because iCloud forwarding is unreliable.
.env:  OTP_WEBHOOK_URL=https://discord.com/api/webhooks/...   (a channel in your own server)
Test:  python otp_watch.py
"""
import email
import email.utils
import imaplib
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

import important
from spapi import load_env, uk_now, uk_offset

ROOT = Path(__file__).parent
STATE = ROOT / "otp_state.json"
LOOKBACK_DAYS = 3

CARRIER_TERMS = ["amazon", "dpd", "evri", "hermes", "royalmail", "parcelforce", "dhl", "yodel", "ups.com", "fedex", "inpost"]
# Who the parcel is for, from the delivery town in the email (towns come from .env)
_ENV = load_env()
PREP_TOWN = _ENV.get("PREP_TOWN", "Prepton")        # town of the prep centre
HOME_TOWN = _ENV.get("HOME_TOWN", "Hometown")       # town of your own delivery address
RECIPIENT_NAME = _ENV.get("RECIPIENT_NAME", "")     # name on the parcel label, used to spot other towns
DESTINATIONS = [("Prep", re.compile(rf"\b{re.escape(PREP_TOWN)}\b", re.I)), ("Me", re.compile(rf"\b{re.escape(HOME_TOWN)}\b", re.I))]
TOWN_RE = re.compile(rf"\b({re.escape(PREP_TOWN)}|{re.escape(HOME_TOWN)})\b", re.I)
CARRIER_SENDERS = re.compile(r"amazon|dpd|evri|hermes|royalmail|royal mail|parcelforce|ups\.com|dhl|yodel|fedex|inpost", re.I)
SUBJECT_HINT = re.compile(r"one[- ]time password|delivery (code|pin|password)|security code|\bpin\b|\botp\b|code (is )?required|password is required", re.I)
CODE_PATTERNS = [
    re.compile(r"one[- ]time password is[:\s]*([0-9]{4,8})", re.I),
    re.compile(r"(?:delivery|security|one[- ]time|parcel|safe ?place)\s*(?:code|pin|password|passcode)\s*(?:is|:)?\s*([0-9]{4,8})", re.I),
    re.compile(r"(?:give|show|provide|tell) (?:the|your) driver (?:this|the|your)? ?(?:code|pin)[^0-9]{0,30}([0-9]{4,8})", re.I),
]


def _text_nodes(msg):
    """Visible text of the email, built from HTML text nodes (Amazon puts the code only in the HTML)."""
    html, plain = "", ""
    for part in msg.walk():
        ct = part.get_content_type()
        if part.get_content_maintype() == "multipart":
            continue
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            text = payload.decode(part.get_content_charset() or "utf-8", "ignore")
        except Exception:
            continue
        if ct == "text/html" and not html:
            h = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
            nodes = [re.sub(r"[͏‌­\xa0​]+", " ", unescape(n)).strip() for n in re.findall(r">([^<]+)<", h)]
            html = " ".join(n for n in nodes if n)
        elif ct == "text/plain" and not plain:
            plain = text
    return " ".join((html + " " + plain).split())


def extract(msg):
    subject = important._dec(msg.get("Subject"))
    sender_name, sender = email.utils.parseaddr(important._dec(msg.get("From")))
    if not (CARRIER_SENDERS.search(sender) or CARRIER_SENDERS.search(sender_name)):
        return None
    text = _text_nodes(msg)
    code = None
    for pat in CODE_PATTERNS:
        m = pat.search(text)
        if m:
            code = m.group(1)
            break
    if not code:
        return None
    carrier = "Amazon" if re.search(r"amazon", sender, re.I) else "DPD" if re.search(r"dpd", sender, re.I) else (sender_name or sender.split("@")[-1])
    window = re.search(r"arriving (today|tomorrow)\s+([0-9]{1,2}(?::[0-9]{2})?\s*[ap]m\s*[-–]\s*[0-9]{1,2}(?::[0-9]{2})?\s*[ap]m)", text, re.I) \
        or re.search(r"(today|tomorrow)[^.]{0,40}?between\s*([0-9:]{4,5}\s*[-–]\s*[0-9:]{4,5})", text, re.I)
    order = re.search(r"order\s*#?\s*([0-9]{3}-[0-9]{7}-[0-9]{7})", text, re.I)
    parcel = re.search(r"parcel(?: number)?:?\s*([0-9 ]{10,20})", text, re.I)
    item = re.search(r"\*\s*(.{5,90}?)\s+Quantity", text) or re.search(r"Track package\s+(?:Your one-time password is\s*[0-9]+\s*)?(.{5,90}?)\s+Quantity", text)
    town = TOWN_RE.search(text) or (RECIPIENT_NAME and re.search(rf"{re.escape(RECIPIENT_NAME)}\s*[–-]\s*([A-Z][A-Z ]{{2,30}})\b", text))
    dest = next((name for name, pat in DESTINATIONS if pat.search(text)), "Unknown")
    return {
        "code": code, "carrier": carrier, "subject": subject[:160],
        "window": " ".join(x for x in (window.groups() if window else ()) if x) or None,
        "order": order.group(1) if order else None, "parcel": parcel.group(1).strip() if parcel else None,
        "item": item.group(1).strip(" *") if item else None, "town": town.group(1).strip().title() if town else None,
        "dest": dest,
        "to": email.utils.parseaddr(important._dec(msg.get("To")))[1],
    }


def _received(msg):
    try:
        d = email.utils.parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc)
        return (d + uk_offset(d)).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def scan():
    since = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")

    def one(acc):
        addr, pw, host = acc
        got = []
        try:
            M = imaplib.IMAP4_SSL(host, 993, timeout=60)
        except Exception:
            return got
        try:
            M.login(addr, pw)
            M.select("INBOX", readonly=True)
            ids = set()
            for term in CARRIER_TERMS:  # server-side search by carrier, so busy inboxes don't hide codes
                typ, data = M.search(None, f'(SINCE "{since}" FROM "{term}")')
                ids.update((data[0] or b"").split() if data else [])  # iCloud answers [None] when nothing matches
            for i in sorted(ids, key=int):
                typ, hdr = M.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
                h = hdr[0][1].decode("utf-8", "ignore") if hdr and isinstance(hdr[0], tuple) else ""
                h = important._dec(h)
                if not CARRIER_SENDERS.search(h) or not (SUBJECT_HINT.search(h) or re.search(r"arriving|out for delivery|deliver", h, re.I)):
                    continue
                typ, md = M.fetch(i, "(BODY.PEEK[])")
                msg = email.message_from_bytes(md[0][1])
                info = extract(msg)
                if info:
                    info["id"] = (msg.get("Message-ID") or f"{addr}-{i.decode()}").strip()
                    info["received"] = _received(msg).isoformat(timespec="minutes")
                    info["account"] = addr
                    got.append(info)
        except Exception:
            pass   # one slow or broken inbox must not stop codes from the others
        finally:
            try:
                M.logout()
            except Exception:
                pass
        return got

    from concurrent.futures import ThreadPoolExecutor
    found = []
    with ThreadPoolExecutor(max_workers=6) as ex:   # all inboxes at once; map keeps .env order for de-duplication
        for got in ex.map(one, important.imap_accounts()):
            found += got
    uniq = {}
    for f in found:  # same email via two inboxes (forwarding) -> once
        uniq.setdefault(f["id"], f)
    return sorted(uniq.values(), key=lambda x: x["received"], reverse=True)


def _load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


def post_discord(webhook, c):
    when = f" · {c['window']}" if c.get("window") else ""
    fields = [{"name": "Code", "value": f"**`{c['code']}`**", "inline": True},
              {"name": "Carrier", "value": c["carrier"], "inline": True}]
    if c.get("window"):
        fields.append({"name": "Delivery", "value": c["window"], "inline": True})
    for k, label in (("item", "Item"), ("order", "Order"), ("parcel", "Parcel"), ("town", "Deliver to"), ("to", "Sent to")):
        if c.get(k):
            fields.append({"name": label, "value": str(c[k])[:200], "inline": k in ("order", "town", "parcel")})
    who = {"Prep": f"🏭 **PREP ({PREP_TOWN})**", "Me": f"🏠 **YOU ({HOME_TOWN})**"}.get(c.get("dest"), "❓ **Check address**")
    colour = {"Prep": 0xFFC857, "Me": 0x4FF0B4}.get(c.get("dest"), 0x8B7BFF)
    tip = "paste this code into your prep ticket" if c.get("dest") == "Prep" else "for your own delivery"
    payload = {
        "content": f"{who} · 📦 {c['carrier']} delivery code: **{c['code']}**{when}",
        "embeds": [{"title": c["subject"][:250], "color": colour, "fields": fields,
                    "footer": {"text": f"Command Centre · {tip}"}}],
        "allowed_mentions": {"parse": []},
    }
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "CommandCentre/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status in (200, 204)


def build():
    if not important.imap_accounts():
        return {"configured": False}
    codes = scan()
    state = _load_state()
    webhook = load_env().get("OTP_WEBHOOK_URL", "")
    webhook = webhook if webhook.startswith("https://discord.com/api/webhooks/") else ""
    errors, posted_now = [], []
    if state is None:
        # first run: remember what's already there, don't spam old codes
        state = {"posted": [c["id"] for c in codes]}
    elif webhook:
        for c in reversed(codes):
            if c["id"] not in state["posted"]:
                try:
                    if post_discord(webhook, c):
                        state["posted"].append(c["id"])
                        posted_now.append(c["code"])
                except Exception as e:
                    errors.append(f"Discord post failed: {e}")
    state["posted"] = state["posted"][-300:]
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    today = uk_now().date().isoformat()
    for c in codes:
        c["today"] = c["received"][:10] == today
        c["posted"] = c["id"] in state["posted"]
    return {"configured": True, "updated": uk_now().strftime("%H:%M"), "webhook": bool(webhook), "errors": errors,
            "postedNow": posted_now, "codes": codes[:20]}


if __name__ == "__main__":
    d = build()
    print({k: v for k, v in d.items() if k != "codes"})
    for c in d.get("codes", []):
        masked = c["code"][:1] + "•" * (len(c["code"]) - 1)
        print(c["received"], c["carrier"], masked, "|", c.get("window"), "|", (c.get("item") or "")[:40], "|", c.get("order"), "|", c.get("town"), "|", c.get("to"))
