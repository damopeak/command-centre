"""Watchdog: keeps the Command Centre and the deal monitors running 24/7.

Runs every 5 minutes (and at sign-in) from the Windows Task Scheduler task "Command Centre Watchdog".
Each run:
  * starts any service that isn't running (dashboard server + oa-bot monitors)
  * restarts the dashboard if it's running but has stopped answering for two checks in a row
Services are launched through WMI so they're independent of this script, of Claude and of any terminal.
Log: watchdog.log
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

from spapi import load_env

ROOT = Path(__file__).parent
_ENV = load_env()
OA = Path(_ENV.get("OA_BOT_DIR") or ROOT.parent / "oa-bot")
PY = _ENV.get("PYTHONW", r"C:\Python314\pythonw.exe")
LOG = ROOT / "watchdog.log"
STATE = ROOT / "watchdog_state.json"
NO_WINDOW = 0x08000000

# Argos / TK Maxx / Currys monitors switched off at the user's request (11 Oct 2026): only HUKD, DBH (+ manual Discord)
SERVICES = [
    ("Command Centre", ROOT / "server.py", "--no-browser"),
    ("HUKD monitor", OA / "hukd_monitor.py", "--service"),
    ("DBH notifier", OA / "dbh_leads_monitor.py", "--service"),
]


def log(msg):
    if LOG.exists() and LOG.stat().st_size > 1_000_000:
        LOG.replace(LOG.with_suffix(".old.log"))
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                       capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
    return r.stdout.strip()


def python_processes():
    out = ps("Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | "
             "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress")
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def launch(script, args):
    cmdline = f'"{PY}" "{script}" {args}'.replace("'", "''")
    cwd = str(script.parent).replace("'", "''")
    ps(f"Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
       f"-Arguments @{{CommandLine='{cmdline}'; CurrentDirectory='{cwd}'}} | Out-Null")


def server_healthy():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    procs = python_processes()

    def running(script):
        return [p for p in procs if p.get("CommandLine") and script.name.lower() in p["CommandLine"].lower()]

    for name, script, args in SERVICES:
        if not script.exists():
            continue
        found = running(script)
        if not found:
            launch(script, args)
            state[f"started:{script.name}"] = time.time()
            log(f"{name} wasn't running, started it")
            continue
        if script.name == "server.py":
            # Running but frozen? Restart after two failed checks (and not while it's still booting)
            booted = time.time() - state.get("started:server.py", 0) > 180
            if server_healthy():
                state["server_fails"] = 0
            elif booted:
                state["server_fails"] = state.get("server_fails", 0) + 1
                log(f"Command Centre not answering ({state['server_fails']} check(s) in a row)")
                if state["server_fails"] >= 2:
                    for p in found:
                        ps(f"Stop-Process -Id {int(p['ProcessId'])} -Force")
                    time.sleep(3)
                    launch(script, args)
                    state["server_fails"] = 0
                    state["started:server.py"] = time.time()
                    log("Command Centre restarted")
    state["lastRun"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"watchdog error: {e!r}")
