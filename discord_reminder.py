"""Windows notification every 6 hours: "time to check your Discord leads".

Run by a Windows Task Scheduler task "Discord Leads Reminder" (09:00, 15:00, 21:00, 03:00).
Skipped if a check already happened in the last 6 hours and during quiet hours (00:00-07:00).
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
NO_WINDOW = 0x08000000
APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def last_check():
    try:
        d = json.loads((ROOT / "discord_leads.json").read_text(encoding="utf-8"))
        return datetime.fromisoformat(d["lastCheck"])
    except Exception:
        return None


def toast(title, body):
    xml = (f"<toast scenario='reminder'><visual><binding template='ToastGeneric'><text>{title}</text><text>{body}</text>"
           "</binding></visual><actions><action content='Dismiss' arguments='dismiss' activationType='system'/></actions></toast>")
    ps = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml(@'
{xml}
'@)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_ID}').Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], creationflags=NO_WINDOW, timeout=60)


def main():
    now = datetime.now()
    if now.hour < 7:
        return  # quiet hours
    lc = last_check()
    if lc and (now - lc).total_seconds() < 6 * 3600:
        return  # checked recently
    ago = ""
    if lc:
        h = int((now - lc).total_seconds() // 3600)
        ago = f"Last check {h // 24} days ago. " if h >= 48 else f"Last check {h}h ago. "
    toast("🔎 Time to check Discord leads", f"{ago}Tell Claude: \"check my Discord leads\"")


if __name__ == "__main__":
    main()
