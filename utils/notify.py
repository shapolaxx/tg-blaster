import subprocess


def notify(title: str, message: str) -> None:
    # Pass title/message as separate -ArgumentList params to avoid any injection
    script = (
        "param($t,$m); "
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Application; "
        "$n.Visible = $true; "
        "$n.ShowBalloonTip(6000, $t, $m, [System.Windows.Forms.ToolTipIcon]::None); "
        "Start-Sleep -Seconds 7; $n.Dispose()"
    )
    try:
        subprocess.Popen(
            [
                "powershell", "-WindowStyle", "Hidden", "-NonInteractive",
                "-Command", script,
                "-t", title,
                "-m", message,
            ],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass
