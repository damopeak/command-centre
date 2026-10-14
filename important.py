"""Important emails: read-only IMAP scan of Gmail inboxes, scored by rules, for the Important tab.

.env (one line per account; app password from myaccount.google.com/apppasswords):
    GMAIL_1=you@example.com|abcd efgh ijkl mnop
The mailbox is opened READ-ONLY and bodies are fetched with BODY.PEEK, so nothing is marked as read.
Test:  python important.py
"""
import email
import email.header
import email.utils
import imaplib
import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import quote

from spapi import load_env, uk_now, uk_offset

DAYS = 5
MAX_PER_ACCOUNT = 250

# category, priority (1 = high), reason, pattern on subject + start of body
RULES = [
    ("Job", 1, "Interview / assessment invite", r"\binterview|assessment cent(re|er)|online assessment|video assessment|hirevue|screening call|invitation to (an )?(interview|assessment)|complete your (assessment|test)|next stage|shortlisted"),
    ("Job", 1, "Job offer", r"job offer|offer of employment|offer letter|conditional offer|pleased to offer you (the|a|this) (position|role|job|place)|we('d| would) like to offer you (the|a) (position|role|job)"),
    ("Job", 2, "Application update", r"your application|application (status|update)|unfortunately|not (been )?successful|regret to inform|thank you for applying"),
    ("Money", 1, "Payment problem", r"payment (failed|declined|unsuccessful)|card (was )?declined|transactions? (may be|will be|were) declined|approaching your (card|credit) limit|over your (credit )?limit|overdue|final (notice|reminder)|unpaid|missed payment|insufficient funds"),
    ("Money", 1, "HMRC / tax", r"\bhmrc\b|self assessment|tax return|\bvat\b (return|payment)|companies house|corporation tax"),
    ("Business", 1, "Amazon account alert", r"account health|policy (warning|violation)|listing (removed|deactivated|suppressed)|deactivat|suspend|seller performance|restricted|intellectual property|counterfeit|authenticity"),
    ("Business", 2, "Amazon / reimbursement", r"seller central|reimbursement|fba (shipment|inventory)|removal order|amazon (payments|disbursement)|settlement"),
    ("Money", 2, "Bills & invoices", r"invoice|bill is ready|statement is ready|direct debit|payment (due|reminder|received|confirmation)|refund"),
    ("Security", 1, "Security alert", r"security alert|new sign-?in|sign-?in attempt|suspicious|password (changed|reset)|unusual activity|verify (it'?s|your) (you|identity)|2-step|two-factor"),
    ("Life", 1, "Missed delivery / collection", r"(collection|delivery) (attempt )?(was |has been )?(unsuccessful|failed|missed)|(unsuccessful|failed|missed) (collection|delivery)|collection attempt|we (tried|attempted) to (deliver|collect)|sorry we missed you|rearrange (your )?(delivery|collection)|re-?book (a |the |your )?(collection|delivery)|returned to sender"),
    ("Life", 2, "Appointment / booking", r"appointment|booking (confirmed|confirmation|reference)|reservation|your booking|tickets?\b.*(confirmed|order)|check-?in|e-?ticket|gp surgery|dentist|hospital|nhs"),
    ("Life", 3, "Delivery", r"out for delivery|delivered|dispatched|has shipped|on its way|arriving (today|tomorrow)|delivery (date|slot|update)|parcel|collect(ion)? (point|from)|ready (for|to) collect"),
]
JOB_ALERT_SENDERS = re.compile(r"totaljobs|brightnetwork|linkedin|indeed|reed\.co|glassdoor|gradcracker|prospects|milkround|targetjobs|cv-library|jobsite|monster|ziprecruiter|adzuna|otta|welcometothejungle", re.I)
PROMO = re.compile(r"\d+\s?% off|£\s?\d+ off|half[- ]price|free (month|trial|delivery)|\btrial\b|final (call|chance|clearance)|clearance|almost gone|going, going|it[’']?s .{0,40} time!|last chance|\bsale\b|\bdeals?\b|discount|voucher|promo|members week|ends? tonight|don'?t miss|exclusive|save (up to|£)|get up to|cashback|payday offer|webinar|upcoming event|join us|register (now|today)|build (your )?skills|insight (day|event)|open (day|evening)|we['’]?re hiring|survey|your view", re.I)
SKIP = re.compile(r"verification code|one[- ]time (pass)?code|\botp\b|passcode|safekey|your code is|sign in to your google account|order (is )?confirm|thanks for your order|thank you for your order|^ordered:|bestellt|willkommen|welcome to|job alert", re.I)
PERSONAL_DOMAINS = re.compile(r"@(gmail|googlemail|outlook|hotmail|live|icloud|me|yahoo|aol|proton(mail)?)\.", re.I)
NOREPLY = re.compile(r"no-?reply|donotreply|do-not-reply|notifications?@|alerts?@|news(letter)?@|marketing|mailer|info@|hello@|team@", re.I)

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
DATE_RE = re.compile(
    rf"(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})[a-z]*\.?(?:,?\s+(20\d\d))?"
    rf"|({MONTHS})[a-z]*\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?"
    r"|\b(\d{1,2})/(\d{1,2})/(20\d\d)\b", re.I)
TIME_RE = re.compile(r"\b(\d{1,2})(?::|\.)(\d{2})\s*(am|pm)?\b|\b(\d{1,2})\s*(am|pm)\b", re.I)
MONTH_NUM = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def accounts():
    env = load_env()
    out = []
    for k in sorted(env):
        if k.startswith("GMAIL_") and "|" in env[k]:
            addr, pw = env[k].split("|", 1)
            pw = pw.replace(" ", "").strip()
            if "@" in addr and pw and "paste" not in pw:
                out.append((addr.strip(), pw))
    return out


def imap_accounts():
    """All read-only mail logins as (address, app password, IMAP host): GMAIL_n plus ICLOUD_n."""
    env = load_env()
    out = [(a, p, "imap.gmail.com") for a, p in accounts()]
    for k in sorted(env):
        if k.startswith("ICLOUD_") and "|" in env[k]:
            addr, pw = env[k].split("|", 1)
            pw = pw.strip()
            if "@" in addr and pw and "paste" not in pw:
                out.append((addr.strip(), pw, "imap.mail.me.com"))
    return out


def _dec(v):
    if not v:
        return ""
    parts = []
    for text, enc in email.header.decode_header(v):
        parts.append(text.decode(enc or "utf-8", "ignore") if isinstance(text, bytes) else text)
    return " ".join("".join(parts).split())


def _body_text(msg, limit=1500):
    plain, html = None, None
    for part in msg.walk():
        ct = part.get_content_type()
        if part.get_content_maintype() == "multipart" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            text = payload.decode(part.get_content_charset() or "utf-8", "ignore")
        except Exception:
            continue
        if ct == "text/plain" and plain is None:
            plain = text
        elif ct == "text/html" and html is None:
            html = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
            html = unescape(re.sub(r"<[^>]+>", " ", html))
    text = unescape(plain or html or "")  # plain parts can still carry entities like &#39;
    return " ".join(text.split())[:limit]


def _find_date(text, received):
    """First future-ish date (+ time) mentioned, for the Add-to-calendar button."""
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        if m.group(1):
            day, mon, year = int(m.group(1)), MONTH_NUM[m.group(2).lower()[:3]], m.group(3)
        elif m.group(4):
            day, mon, year = int(m.group(5)), MONTH_NUM[m.group(4).lower()[:3]], m.group(6)
        else:
            day, mon, year = int(m.group(7)), int(m.group(8)), m.group(9)
        had_year = bool(year)
        d = datetime(int(year) if year else received.year, mon, day)
        if not had_year and d.date() < received.date() - timedelta(days=1):
            d = d.replace(year=d.year + 1)  # "5 Jan" in a December email means next year
    except (ValueError, KeyError):
        return None
    if d.date() < received.date() - timedelta(days=1) or d.date() > received.date() + timedelta(days=200):
        return None
    tail = text[m.end():m.end() + 60]
    t = TIME_RE.search(tail) or TIME_RE.search(text[max(0, m.start() - 40):m.start()])
    if t:
        h = int(t.group(1) or t.group(4))
        mins = int(t.group(2) or 0)
        ap = (t.group(3) or t.group(5) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        if 0 <= h < 24:
            return d.replace(hour=h, minute=mins), True
    return d, False


def _gcal_link(title, when, timed, details):
    if timed:
        start = when
        end = when + timedelta(hours=1)
        # Google wants UTC "Z" times; convert from UK local
        off = uk_offset(start.replace(tzinfo=timezone.utc))
        fmt = lambda x: (x - off).strftime("%Y%m%dT%H%M%SZ")
        dates = f"{fmt(start)}/{fmt(end)}"
    else:
        dates = f"{when.strftime('%Y%m%d')}/{(when + timedelta(days=1)).strftime('%Y%m%d')}"
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={quote(title[:120])}&dates={dates}&details={quote(details[:600])}")


REJECTION = re.compile(
    r"unfortunately|regret to (inform|let you know)|not (been )?successful|unsuccessful|not (be )?(progressing|moving forward|taking your application)|"
    r"decided not to (progress|proceed|move)|won['’]?t be (progressing|moving|taking)|will not be (progressing|moving|taking)|"
    r"other candidates|more closely match|not able to offer you|no longer (being )?considered|position has (now )?been filled|"
    r"role has been (cancelled|filled|withdrawn)|we (have|ve) decided to|wish you (every|all the) (success|best) in your (job )?search|felt humbled", re.I)


JOB_CONTEXT = re.compile(r"\bapplication|\bapplied|\bapplying|candidate|\brole\b|position|vacanc|recruit|graduate|internship|talent acquisition|hiring|interview|assessment|programme", re.I)


def score(subject, body, sender, headers, labels):
    if SKIP.search(subject):  # one-time codes, order confirmations, welcome mails, job alerts
        return None
    head = f"{subject} {body[:1500]}"
    # Google's notices about changes the user made themselves (app passwords, 2-Step on, copies to the recovery address)
    if re.search(r"google", sender, re.I) and re.search(
            r"app password (was )?created|2-step verification (is )?(turned on|enabled)|is now protected with 2-step|"
            r"recovery (email|phone)[^.]{0,40}(changed|added|updated)", head, re.I) \
            and not re.search(r"suspicious|blocked|critical|someone (else )?(has|knows)|unusual|new sign-?in", head, re.I):
        return None
    # copies sent to a recovery address: every account is connected now, so the original alert already shows
    if re.search(r"google", sender, re.I) and re.search(r"this is a copy of a security alert sent to", head, re.I):
        return None
    # routine "new sign-in on Windows/Mac... if this was you, you don't need to do anything": low, not High
    if re.search(r"google", sender, re.I) and re.search(r"new sign-?in", head, re.I) \
            and re.search(r"if this was you,? you don.?t need to do anything", head, re.I) \
            and not re.search(r"suspicious|blocked|critical|someone (else )?(has|knows)|unusual", head, re.I):
        return (3, "Security", "New sign-in notice (if it was you, nothing to do)")
    if JOB_CONTEXT.search(head) and REJECTION.search(head):  # job rejections only (not e.g. "collection unsuccessful")
        return None
    bulk = bool(headers.get("List-Unsubscribe")) or (headers.get("Precedence", "").lower() in ("bulk", "list"))
    # newsletters only count when the subject itself says it; personal mail can match the opening lines too
    text = subject.lower() if bulk else f"{subject} {body[:600]}".lower()
    hits = []
    for cat, prio, reason, pat in RULES:
        if re.search(pat, text, re.I):
            hits.append((prio, cat, reason))
    job_alert = bool(JOB_ALERT_SENDERS.search(sender))
    gmail_important = "\\Important" in labels
    is_reply = bool(re.match(r"\s*(re|fwd?|aw|wg)\s*:", subject, re.I))
    person = not bulk and not NOREPLY.search(sender) and (bool(PERSONAL_DOMAINS.search(sender)) or is_reply)
    promo = bool(PROMO.search(subject))

    if job_alert:  # job boards (alerts, community posts) are never personal invites
        return None
    if re.search(r"thank(s| you) for (completing|submitting|applying|your (application|interest))|(received|got) your application|application (received|confirmation)|we have received", subject, re.I)             and not re.search(r"unfortunately|regret|not (been )?successful|next step|invit|complete", subject, re.I):
        hits = [(3, "Job", "Application received")]  # acknowledgements: low priority
    if promo:  # marketing wording: only security alerts and real payment problems survive
        hits = [h for h in hits if h[1] == "Security" or h[2] == "Payment problem"]
    if not hits and person and not promo:
        hits = [(2, "People", "Personal email from a real person")]
    if not hits and gmail_important and not bulk and not promo:
        hits = [(3, "Other", "Gmail marked it important")]
    if not hits:
        return None
    hits.sort()
    prio, cat, reason = hits[0]
    if gmail_important and prio == 3:
        prio = 2  # Gmail's own importance nudges low -> medium, never to high
    return prio, cat, reason


def gmail_link(addr, thread_id, msg_id):
    """Gmail's own deep-link format (the /u/<email>/ path form 404s)."""
    base = f"https://mail.google.com/mail/?authuser={addr}"
    if thread_id and msg_id:
        return f"{base}#all/thread-f:{thread_id}|msg-f:{msg_id}"
    return f"{base}#inbox"


def scan(addr, pw, host="imap.gmail.com"):
    since = (datetime.now() - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    gm = "gmail" in host
    M = imaplib.IMAP4_SSL(host, 993, timeout=30)
    try:
        M.login(addr, pw)
        M.select("INBOX", readonly=True)
        typ, data = M.search(None, f'(SINCE "{since}")')
        ids = data[0].split()[-MAX_PER_ACCOUNT:]
        out = []
        for i in reversed(ids):
            typ, msg_data = M.fetch(i, "(X-GM-MSGID X-GM-THRID X-GM-LABELS FLAGS BODY.PEEK[]<0.40000>)" if gm else "(FLAGS BODY.PEEK[]<0.40000>)")
            meta = b" ".join(p[0] if isinstance(p, tuple) else p for p in msg_data if p)
            raw = next((p[1] for p in msg_data if isinstance(p, tuple)), b"")
            msg = email.message_from_bytes(raw)
            subject = _dec(msg.get("Subject")) or "(no subject)"
            sender_name, sender_addr = email.utils.parseaddr(_dec(msg.get("From")))
            try:
                received = email.utils.parsedate_to_datetime(msg.get("Date"))
                received = received.astimezone(timezone.utc)
                received = (received + uk_offset(received)).replace(tzinfo=None)
            except Exception:
                received = datetime.now()
            labels = re.search(rb"X-GM-LABELS \((.*?)\)", meta)
            labels = labels.group(1).decode("utf-8", "ignore") if labels else ""
            unread = b"\\Seen" not in meta
            gmid = re.search(rb"X-GM-MSGID (\d+)", meta)
            gthr = re.search(rb"X-GM-THRID (\d+)", meta)
            body = _body_text(msg)
            s = score(subject, body, f"{sender_name} {sender_addr}", msg, labels)
            if not s:
                continue
            prio, cat, reason = s
            item = {
                "id": gmid.group(1).decode() if gmid else f"{addr}-{i.decode()}",
                "account": addr, "from": sender_name or sender_addr, "fromAddr": sender_addr,
                "msgid": (msg.get("Message-ID") or "").strip(),
                "to": email.utils.parseaddr(_dec(msg.get("X-Forwarded-For") or msg.get("Delivered-To") or msg.get("To")))[1],
                "subject": subject[:200], "snippet": body[:260], "received": received.isoformat(timespec="minutes"),
                "unread": unread, "priority": prio, "category": cat, "reason": reason,
                "url": gmail_link(addr, gthr.group(1).decode() if gthr else None, gmid.group(1).decode() if gmid else None) if gm else "https://www.icloud.com/mail/",
            }
            found = _find_date(f"{subject} {body[:1200]}", received) if cat in ("Job", "Life", "Money", "Business", "People") else None
            if found:
                when, timed = found
                item["eventDate"] = when.isoformat(timespec="minutes")
                item["eventTimed"] = timed
                item["calendarUrl"] = _gcal_link(subject, when, timed, f"From {sender_name or sender_addr}: {item['url']}")
            out.append(item)
        return out
    finally:
        try:
            M.logout()
        except Exception:
            pass


def build():
    skip = {a.strip().lower() for a in load_env().get("IMPORTANT_SKIP", "").split(",") if a.strip()}
    accs = [a for a in imap_accounts() if a[0].lower() not in skip]   # e.g. a spam-heavy inbox: codes/orders/deadlines only
    if not accs:
        return {"configured": False}
    items, errors = [], []
    from concurrent.futures import ThreadPoolExecutor

    def one(a):
        addr, pw, host = a
        try:
            return scan(addr, pw, host), None
        except imaplib.IMAP4.error as e:
            return [], f"{addr}: {'Gmail' if 'gmail' in host else 'iCloud'} refused the login — check the app password ({e})"
        except Exception as e:
            return [], f"{addr}: {e}"
    with ThreadPoolExecutor(max_workers=6) as ex:
        for got, err in ex.map(one, accs):  # map keeps .env order, so the original inbox still wins de-duplication
            items += got
            if err:
                errors.append(err)
    # spam waves: one display name ("UEFA Champions League") sent from many throwaway personal addresses
    addrs_by_name = {}
    for x in items:
        if PERSONAL_DOMAINS.search(x["fromAddr"]):
            addrs_by_name.setdefault(x["from"].strip().lower(), set()).add(x["fromAddr"].lower())
    spam_names = {n for n, a in addrs_by_name.items() if len(a) >= 3}
    items = [x for x in items if not (PERSONAL_DOMAINS.search(x["fromAddr"]) and x["from"].strip().lower() in spam_names)]
    uniq, seen_ids = [], set()
    for x in items:  # accounts are scanned in .env order, so the original inbox wins over the forwarded copy
        if x["msgid"] and x["msgid"] in seen_ids:
            continue
        seen_ids.add(x["msgid"])
        uniq.append(x)
    items = uniq
    items.sort(key=lambda x: x["received"], reverse=True)   # newest first...
    grouped, seen = [], {}
    for x in items:  # same sender + subject (e.g. 5x "Payment declined") -> one row with a count
        k = (x["fromAddr"].lower(), re.sub(r"\W+", " ", x["subject"].lower()).strip())
        if k in seen:
            seen[k]["count"] = seen[k].get("count", 1) + 1
            seen[k]["unread"] = seen[k]["unread"] or x["unread"]
            continue
        seen[k] = x
        x["groupKey"] = "|".join(k)
        grouped.append(x)
    items = grouped
    items.sort(key=lambda x: x["priority"])                 # ...within each priority (stable sort)
    counts = {p: sum(1 for x in items if x["priority"] == p) for p in (1, 2, 3)}
    return {"configured": True, "updated": uk_now().strftime("%H:%M"), "errors": errors, "accounts": [a for a, _, _ in accs],
            "days": DAYS, "counts": counts, "unreadHigh": sum(1 for x in items if x["priority"] == 1 and x["unread"]), "items": items}


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: v for k, v in d.items() if k != "items"}, indent=1))
    for x in d.get("items", [])[:25]:
        print(x["priority"], x["category"], "|", x["reason"], "|", x["from"][:25], "|", x["subject"][:60], "|", x.get("eventDate", ""))
