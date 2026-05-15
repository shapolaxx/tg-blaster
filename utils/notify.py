import subprocess


def notify(title: str, message: str) -> None:
    safe_title = title.replace("'", "''")
    safe_msg = message.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Application; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(6000, '{safe_title}', '{safe_msg}', "
        "[System.Windows.Forms.ToolTipIcon]::None); "
        "Start-Sleep -Seconds 7; "
        "$n.Dispose()"
    )
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass
