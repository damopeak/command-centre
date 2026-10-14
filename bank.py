"""Bank feeds through TrueLayer (Open Banking, read-only).

You approve access on your bank's own page; we only ever get read-only tokens (never your login).
Tokens: bank_tokens.json (local only). Transactions: bank_transactions.json (last 90 days, all connections).
Sandbox while the client id starts with "sandbox-"; live otherwise.
"""
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from spapi import load_env

ROOT = Path(__file__).parent
TOKENS = ROOT / "bank_tokens.json"
TXNS = ROOT / "bank_transactions.json"
DAYS = 90
SCOPES = "info accounts balance cards transactions offline_access"
_pending = {}   # state -> redirect_uri (CSRF protection for the connect flow)


def _cfg():
    e = load_env()
    cid, sec = e.get("TRUELAYER_CLIENT_ID", ""), e.get("TRUELAYER_CLIENT_SECRET", "")
    sandbox = cid.startswith("sandbox-")
    return {
        "id": cid, "secret": sec, "sandbox": sandbox,
        "auth": "https://auth.truelayer-sandbox.com" if sandbox else "https://auth.truelayer.com",
        "api": "https://api.truelayer-sandbox.com" if sandbox else "https://api.truelayer.com",
        "ok": bool(cid and sec and "paste" not in cid and "paste" not in sec),
    }


def _load():
    try:
        return json.loads(TOKENS.read_text(encoding="utf-8"))
    except Exception:
        return {"connections": []}


def _save(d):
    TOKENS.write_text(json.dumps(d, indent=1), encoding="utf-8")


def connect_url(redirect_uri):
    c = _cfg()
    state = secrets.token_urlsafe(16)
    _pending[state] = redirect_uri
    providers = "uk-cs-mock uk-ob-all uk-oauth-all" if c["sandbox"] else "uk-ob-all uk-oauth-all"
    q = urllib.parse.urlencode({"response_type": "code", "client_id": c["id"], "scope": SCOPES, "redirect_uri": redirect_uri,
                                "providers": providers, "state": state})
    return f"{c['auth']}/?{q}"


def _token(form):
    c = _cfg()
    data = urllib.parse.urlencode({**form, "client_id": c["id"], "client_secret": c["secret"]}).encode()
    req = urllib.request.Request(c["auth"] + "/connect/token", data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _api(conn, path):
    """GET a Data API path, refreshing the access token when needed."""
    c = _cfg()
    if time.time() > conn.get("expires", 0) - 60:
        t = _token({"grant_type": "refresh_token", "refresh_token": conn["refresh"]})
        conn.update({"access": t["access_token"], "refresh": t.get("refresh_token", conn["refresh"]), "expires": time.time() + t["expires_in"]})
    req = urllib.request.Request(c["api"] + path, headers={"Authorization": f"Bearer {conn['access']}"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r).get("results", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        raise RuntimeError(f"{path}: {e.code} {body}") from e


def callback(code, state):
    redirect_uri = _pending.pop(state, None)
    if not redirect_uri:
        raise ValueError("This bank link has expired or was already used. Click Connect bank again.")
    t = _token({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})
    conn = {"id": secrets.token_hex(4), "access": t["access_token"], "refresh": t.get("refresh_token"),
            "expires": time.time() + t["expires_in"], "connected": datetime.now().isoformat(timespec="minutes")}
    info = []
    try:
        info = _api(conn, "/data/v1/me")
    except Exception:
        pass
    p = (info[0].get("provider") or {}) if info else {}
    conn["provider"] = p.get("display_name") or p.get("provider_id") or "Bank"
    conn["providerId"] = p.get("provider_id")
    # consent lasts 90 days for UK Open Banking
    conn["consentExpires"] = (datetime.now() + timedelta(days=90)).date().isoformat()
    d = _load()
    d["connections"] = [x for x in d["connections"] if x.get("providerId") != conn["providerId"] or not conn["providerId"]] + [conn]
    _save(d)
    return conn


def disconnect(cid):
    d = _load()
    d["connections"] = [x for x in d["connections"] if x["id"] != cid]
    _save(d)


def sync():
    """Pull accounts, cards and the last DAYS of transactions for every connection."""
    c = _cfg()
    if not c["ok"]:
        return {"configured": False}
    d = _load()
    frm = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    to = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources, txns, errors = [], [], []
    for conn in d["connections"]:
        for kind in ("accounts", "cards"):
            try:
                items = _api(conn, f"/data/v1/{kind}")
            except Exception as e:
                if "403" not in str(e) and "501" not in str(e):  # banks without cards/accounts return these
                    errors.append(f"{conn['provider']} {kind}: {e}")
                continue
            for it in items:
                aid = it.get("account_id")
                name = it.get("display_name") or it.get("card_network") or kind[:-1]
                label = f"{conn['provider']} · {name}" + (f" ··{it.get('partial_card_number')}" if it.get("partial_card_number") else "")
                bal = None
                try:
                    b = _api(conn, f"/data/v1/{kind}/{aid}/balance")
                    bal = b[0] if b else None
                except Exception:
                    pass
                sources.append({"id": aid, "kind": kind[:-1], "label": label, "provider": conn["provider"], "currency": it.get("currency"),
                                "balance": bal and (bal.get("current") if bal.get("current") is not None else bal.get("available")),
                                "creditLimit": bal and bal.get("credit_limit"), "connection": conn["id"]})
                try:
                    rows = _api(conn, f"/data/v1/{kind}/{aid}/transactions?from={frm}&to={to}")
                except Exception as e:
                    errors.append(f"{label}: {e}")
                    continue
                for t in rows:
                    txns.append({
                        "id": t.get("transaction_id"), "date": (t.get("timestamp") or "")[:10], "time": t.get("timestamp"),
                        "amount": t.get("amount"), "currency": t.get("currency"), "description": t.get("description") or "",
                        "merchant": t.get("merchant_name") or "", "type": t.get("transaction_type"),
                        "category": t.get("transaction_category"), "classification": t.get("transaction_classification") or [],
                        "source": label, "sourceId": aid, "provider": conn["provider"],
                    })
    _save(d)  # persist refreshed tokens
    txns.sort(key=lambda t: t["time"] or "", reverse=True)
    out = {"configured": True, "sandbox": c["sandbox"], "updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "errors": errors,
           "connections": [{k: x.get(k) for k in ("id", "provider", "connected", "consentExpires")} for x in d["connections"]],
           "sources": sources, "transactions": txns}
    TXNS.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def cached():
    try:
        return json.loads(TXNS.read_text(encoding="utf-8"))
    except Exception:
        c = _cfg()
        return {"configured": c["ok"], "sandbox": c["sandbox"], "connections": [], "sources": [], "transactions": []}


# ---------- CSV exports (bank_exports/) ----------
EXPORTS = ROOT / "bank_exports"


def _num(s):
    try:
        return float(str(s).replace(",", "").replace("£", "").strip())
    except ValueError:
        return None


def _dmy(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip()[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def load_csv():
    """Read every CSV in bank_exports/. Money out is negative, money in positive (TrueLayer convention)."""
    import csv
    import hashlib
    out, files = [], []
    for f in sorted(EXPORTS.glob("*.csv")):
        try:
            rows = list(csv.DictReader(f.open(encoding="utf-8-sig", newline="")))
        except Exception:
            continue
        if not rows:
            continue
        h = set(rows[0].keys())
        kind = ("capitalontap" if {"Clearance Date", "Merchant Name", "Card Ending"} <= h else
                "amex" if {"Date", "Description", "Amount"} <= h and any("Card Member" in k or "Account #" in k for k in h) else
                "revolut" if {"Date started (UTC)", "Amount", "Description"} <= h or {"Completed Date", "Amount", "Description"} <= h else None)
        files.append({"file": f.name, "rows": len(rows), "format": kind or "unknown"})
        for i, r in enumerate(rows):
            if kind == "capitalontap":
                amt = _num(r["Amount"])
                if amt is None:
                    continue
                ocur = (r.get("Original Currency") or "").strip() or "GBP"
                t = {"date": _dmy(r.get("Authorisation Date") or r["Clearance Date"]) or _dmy(r["Clearance Date"]),
                     "amount": -amt, "currency": "GBP", "description": r["Description"].split(" - Card Ending")[0].strip(),
                     "merchant": (r.get("Merchant Name") or "").strip(), "type": r.get("Transaction Type"),
                     "category": r.get("Category"), "classification": [r.get("Category")] if r.get("Category") else [],
                     "origAmount": -(_num(r.get("Original Amount")) or amt), "origCurrency": ocur,
                     "source": f"Capital on Tap ··{r.get('Card Ending', '').strip()}", "provider": "Capital on Tap (CSV)"}
            elif kind == "amex":
                amt = _num(r["Amount"])
                if amt is None:
                    continue
                t = {"date": _dmy(r["Date"]), "amount": -amt, "currency": "GBP", "description": r["Description"].strip(),
                     "merchant": (r.get("Appears On Your Statement As") or r["Description"]).strip(), "type": None, "category": r.get("Category"),
                     "classification": [r.get("Category")] if r.get("Category") else [], "source": "Amex" + (f" ··{r.get('Account #', '')[-5:]}" if r.get("Account #") else ""),
                     "provider": "Amex (CSV)"}
            elif kind == "revolut":
                amt = _num(r["Amount"])
                if amt is None or (r.get("State") or "COMPLETED").upper() not in ("COMPLETED", ""):
                    continue
                ref = (r.get("Reference") or "").strip()
                oc = (r.get("Orig currency") or "").strip()
                t = {"date": _dmy(r.get("Date completed (UTC)") or r.get("Completed Date") or r.get("Date started (UTC)") or ""),
                     "amount": _num(r.get("Total amount")) if _num(r.get("Total amount")) is not None else amt,
                     "currency": r.get("Payment currency") or r.get("Currency") or "GBP",
                     "description": r["Description"].strip() + (f" · {ref}" if ref else ""),
                     "balance": _num(r.get("Balance")),
                     "origCurrency": oc or None, "origAmount": (-abs(_num(r.get("Orig amount")) or 0) if amt < 0 else abs(_num(r.get("Orig amount")) or 0)) if oc else None,
                     "merchant": (r.get("Description") or "").strip(), "type": r.get("Type"), "category": r.get("Category"), "classification": [],
                     "source": "Revolut Business" + (f" · {r.get('Account')}" if r.get("Account") else ""), "provider": "Revolut (CSV)"}
            else:
                continue
            if not t["date"]:
                continue
            t["time"] = t["date"]
            t["_content"] = f"{t['provider']}|{t['source']}|{t['date']}|{t['amount']:.2f}|{t['description']}"
            t["_legacy"] = "csv-" + hashlib.sha1(f"{f.name}|{i}|{t['date']}|{t['amount']}|{t['description']}".encode()).hexdigest()[:16]
            t["_file"] = f.name
            out.append(t)
    per_file = {}
    for t in out:
        per_file.setdefault((t["_file"], t["_content"]), []).append(t)
    best = {}
    for (fname, content), group in per_file.items():
        if len(group) > len(best.get(content, [])):
            best[content] = group
    # Rows already in the Google Sheet keep the id they were first synced with (bank_id_alias.json),
    # so switching to content-based ids never duplicates them.
    alias_file = ROOT / "bank_id_alias.json"
    try:
        alias = json.loads(alias_file.read_text(encoding="utf-8"))
    except Exception:
        alias = None
    first = alias is None
    alias = alias or {}
    merged = []
    for content, group in best.items():
        for n, t in enumerate(group):
            new_id = "csv-" + hashlib.sha1(f"{content}|{n}".encode()).hexdigest()[:16]
            if first:
                alias[new_id] = t["_legacy"]
            t["id"] = alias.get(new_id, new_id)
            for k in ("_content", "_file", "_legacy"):
                t.pop(k, None)
            merged.append(t)
    if first:
        alias_file.write_text(json.dumps(alias), encoding="utf-8")
    merged.sort(key=lambda t: t["date"], reverse=True)
    return merged, files


def ledger_transactions(days=DAYS):
    """Real transactions for the ledger: CSV exports + live TrueLayer feeds (sandbox test data is excluded)."""
    rows, files = load_csv()
    live = cached()
    if live.get("configured") and not live.get("sandbox"):
        rows += live.get("transactions") or []
    cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
    return [t for t in rows if t["date"] >= cutoff], files
