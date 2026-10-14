"""Google Calendar via secret iCal addresses (read-only, no login).

Add to .env, one per calendar (name|url):
    CALENDAR_ICS_1=Personal|https://calendar.google.com/calendar/ical/.../private-.../basic.ics
    CALENDAR_ICS_2=Work|https://...
Test:  python calendar_feed.py
"""
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone

import icalendar
import recurring_ical_events

from spapi import load_env, uk_now, uk_offset

DAYS_AHEAD = 14
KINDS = [  # first match wins; used for colour-coding
    ("job", r"interview|assessment|screening|recruit|application|graduate|onboarding|offer|\bcall with\b|hirevue|video interview"),
    ("fba", r"fba|amazon|shipment|ups|dpd|collect|click & collect|argos|wholesale|supplier|stock|prep|inbound|ebay|invenno|seller"),
]


def calendars():
    env = load_env()
    out = []
    for k in sorted(env):
        if k.startswith("CALENDAR_ICS"):
            v = env[k]
            name, url = (v.split("|", 1) if "|" in v else (f"Calendar {len(out) + 1}", v))
            if url.startswith("http") and "paste" not in url:
                out.append((name.strip(), url.strip()))
    return out


def _local(dt):
    """Calendar datetime -> naive UK local time."""
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            utc = dt.astimezone(timezone.utc)
            return (utc + uk_offset(utc)).replace(tzinfo=None)
        return dt
    return datetime(dt.year, dt.month, dt.day)


def _kind(text):
    low = text.lower()
    for kind, pattern in KINDS:
        if re.search(pattern, low):
            return kind
    return "life"


def build():
    cals = calendars()
    if not cals:
        return {"configured": False}
    today = uk_now().date()
    start = datetime(today.year, today.month, today.day) - timedelta(days=1)
    end = start + timedelta(days=DAYS_AHEAD + 2)
    events, errors = [], []
    for name, url in cals:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CommandCentre/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                cal = icalendar.Calendar.from_ical(r.read())
            for ev in recurring_ical_events.of(cal).between(start, end):
                s, e = ev.get("DTSTART").dt, (ev.get("DTEND").dt if ev.get("DTEND") else None)
                all_day = not isinstance(s, datetime)
                ls = _local(s)
                le = _local(e) if e else ls + (timedelta(days=1) if all_day else timedelta(hours=1))
                title = str(ev.get("SUMMARY") or "(no title)")
                loc = str(ev.get("LOCATION") or "")
                desc = str(ev.get("DESCRIPTION") or "")
                events.append({
                    "title": title, "start": ls.isoformat(), "end": le.isoformat(), "allDay": all_day,
                    "location": loc[:120], "calendar": name, "kind": _kind(f"{title} {loc} {desc[:200]}"),
                })
        except Exception as e:
            errors.append(f"{name}: {e}")
    events = [e for e in events if datetime.fromisoformat(e["end"]) > start]
    events.sort(key=lambda e: (e["start"], not e["allDay"]))
    # de-duplicate the same event appearing in two calendars
    seen, uniq = set(), []
    for e in events:
        k = (e["title"], e["start"])
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return {"configured": True, "updated": uk_now().strftime("%H:%M"), "errors": errors,
            "calendars": [n for n, _ in cals], "today": str(today), "events": uniq}


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: v for k, v in d.items() if k != "events"}, indent=1))
    for e in d.get("events", [])[:15]:
        print(e["start"][:16], e["kind"], e["calendar"], e["title"][:60])
