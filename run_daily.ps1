# Daily run of Aula Meteo (for the Windows Task Scheduler or by hand); publishes to GitHub Pages.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File run_daily.ps1 [--reuse-text]
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" -m aulameteo.daily --publish @args
$code = $LASTEXITCODE

# A scheduled task fails silently: in Oct-Nov 2026 the web went a week without updating unnoticed.
# On failure, show a Windows notification with what to do.
if ($code -ne 0) {
    try {
        $log = Join-Path $PSScriptRoot "data\logs\$(Get-Date -Format yyyy-MM).log"
        $tail = @(if (Test-Path $log) { Get-Content $log -Tail 80 -Encoding UTF8 })
        $today = Get-Date -Format yyyy-MM-dd
        $start = [array]::FindLastIndex($tail, [Predicate[string]]{ param($l) $l.StartsWith($today) -and $l -match " ERROR " })
        $error_lines = if ($start -ge 0) { $tail[$start..($tail.Count - 1)] } else { @() }  # only today's error
        $hint = if ($error_lines -match "gh auth login") {
            "Ha caducado el login de GitHub. Ejecuta: gh auth login -h github.com y luego .\run_daily.ps1 --rebuild-site"
        } else {
            "Mira el registro: data\logs\$(Get-Date -Format yyyy-MM).log"
        }
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $lines = $xml.GetElementsByTagName("text")
        $lines.Item(0).AppendChild($xml.CreateTextNode("Aula Meteo: la clase de hoy no se ha publicado")) | Out-Null
        $lines.Item(1).AppendChild($xml.CreateTextNode($hint)) | Out-Null
        $powershell = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"  # a registered app id
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($powershell).Show(
            [Windows.UI.Notifications.ToastNotification]::new($xml))
    } catch { }  # the notification is a courtesy; the exit code still marks the task as failed
}
exit $code
