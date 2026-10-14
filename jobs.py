"""Job hunt connector: reads a companion job-dashboard site's APIs (Airtable jobs + application tracker Sheet).

The site URL and key live in .env as JOB_DASHBOARD_URL and JOB_DASHBOARD_KEY.
Test:  python jobs.py
"""
import json
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from spapi import load_env, uk_now

JOB_SITE = load_env().get("JOB_DASHBOARD_URL", "https://job-dashboard.example.com/").rstrip("/") + "/"
BASE = JOB_SITE + "api/"

WAITING = {"Applied, waiting for response", "Waiting for response", "Awaiting reply"}
IN_PROCESS = {"Online Assessment", "Online Questions", "Screening Call", "Assessment Centre", "Assessment", "Interview",
              "First Interview", "Second Interview", "Final Interview"}
OFFER_WORDS = ("offer",)
REJECT_WORDS = ("denied", "rejected", "unsuccessful")
TOP_RATING = 9  # ratings are out of 10; most open jobs score 7-8, so 9+ is the useful "top match" cut


def _get(path, key):
    req = urllib.request.Request(BASE + path, headers={"x-dashboard-key": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _stage(status):
    s = (status or "").strip()
    low = s.lower()
    if any(w in low for w in OFFER_WORDS):
        return "offer"
    if any(w in low for w in REJECT_WORDS):
        return "rejected"
    if s in IN_PROCESS or "interview" in low or "assessment" in low or "screening" in low or "questions" in low:
        return "process"
    return "waiting"


def _d(s):
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def build():
    key = load_env().get("JOB_DASHBOARD_KEY")
    if not key:
        return {"configured": False}
    jobs = _get("jobs", key).get("jobs", [])
    rows = _get("tracker", key).get("rows", [])
    updates = _get("updates", key).get("entries", [])

    today = uk_now().date()
    week_ago = today - timedelta(days=6)

    # New matches: not yet applied/dismissed, best first, newest first
    open_jobs = [j for j in jobs if (j.get("status") or "Not applied") == "Not applied"]
    for j in open_jobs:
        j["_found"] = _d(j.get("dateFound"))
    top = [j for j in open_jobs if (j.get("rating") or 0) >= TOP_RATING]
    # Newest top-rated jobs first: this week's 9-10s, best rating first within each day
    matches = sorted(top, key=lambda j: (j["_found"] or date.min, j.get("rating") or 0), reverse=True)
    found_today = sum(1 for j in open_jobs if j["_found"] == today)
    found_week = sum(1 for j in open_jobs if j["_found"] and j["_found"] >= week_ago)
    good_week = sum(1 for j in top if j["_found"] and j["_found"] >= week_ago)
    good_today = sum(1 for j in top if j["_found"] == today)

    # Pipeline from the tracker sheet
    stages = Counter(_stage(r.get("status")) for r in rows if r.get("company"))
    in_process = [r for r in rows if r.get("company") and _stage(r.get("status")) in ("process", "offer")]
    deadlines = []
    for r in rows:
        dl = (r.get("deadline") or "").strip()
        if not dl or _stage(r.get("status")) == "rejected":
            continue
        parsed = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
            try:
                parsed = datetime.strptime(dl, fmt).date()
                break
            except ValueError:
                pass
        if parsed and parsed >= today - timedelta(days=1):
            deadlines.append({"company": r.get("company"), "role": r.get("role"), "status": r.get("status"),
                              "deadline": str(parsed), "days": (parsed - today).days})
    deadlines.sort(key=lambda x: x["days"])

    # Activity from the daily changes log
    for u in updates:
        u["_d"] = _d(u.get("isoDate"))
    recent = sorted([u for u in updates if u["_d"]], key=lambda u: u["_d"], reverse=True)
    applied_by_day = Counter(u["_d"] for u in updates if u["_d"] and "applied" in (u.get("change") or "").lower())
    days30 = [today - timedelta(days=n) for n in range(29, -1, -1)]

    return {
        "configured": True,
        "updated": uk_now().strftime("%H:%M"),
        "site": JOB_SITE,
        "counts": {
            "scraped": len(jobs), "open": len(open_jobs), "foundToday": found_today, "foundWeek": found_week,
            "goodWeek": good_week, "goodToday": good_today, "topTotal": len(top), "applications": sum(stages.values()),
            "appliedWeek": sum(v for d, v in applied_by_day.items() if d >= week_ago),
        },
        "pipeline": [
            {"label": "Top matches · 7d", "n": good_week},
            {"label": "Applied", "n": sum(stages.values())},
            {"label": "Awaiting reply", "n": stages.get("waiting", 0)},
            {"label": "In process", "n": stages.get("process", 0)},
            {"label": "Offers", "n": stages.get("offer", 0)},
            {"label": "Rejected", "n": stages.get("rejected", 0)},
        ],
        "matches": [{"title": j.get("role"), "company": j.get("company"), "location": j.get("location") or "",
                     "salary": j.get("salary") or "", "rating": j.get("rating"), "source": j.get("source"),
                     "url": j.get("url"), "found": str(j["_found"]) if j["_found"] else None} for j in matches[:20]],
        "inProcess": [{"company": r.get("company"), "role": r.get("role"), "status": r.get("status"),
                       "deadline": r.get("deadline") or "", "notes": r.get("notes") or ""} for r in in_process],
        "deadlines": deadlines[:10],
        "recent": [{"date": u.get("isoDate"), "company": u.get("company"), "role": u.get("role"), "change": u.get("change")} for u in recent[:15]],
        "appliedLabels": [f"{d.day} {d.strftime('%b')}" for d in days30],
        "applied30": [applied_by_day.get(d, 0) for d in days30],
    }


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: v for k, v in d.items() if k not in ("matches", "recent")}, indent=1, ensure_ascii=False)[:3000])
    print("top match:", d.get("matches", [None])[0])
