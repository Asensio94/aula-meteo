# Registers (or replaces) the Windows scheduled task that builds the daily page at 11:00.
# Run it once yourself:  powershell -NoProfile -ExecutionPolicy Bypass -File register_task.ps1
# Remove it with:        Unregister-ScheduledTask -TaskName "Aula Meteo" -Confirm:$false
$script = Join-Path $PSScriptRoot "run_daily.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At 11:00
# StartWhenAvailable: if the computer was off at 11:00, run as soon as it is back on.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "Aula Meteo" -Description "Aula Meteo: daily page (ECMWF + Claude)" `
    -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
$info = Get-ScheduledTask -TaskName "Aula Meteo" | Get-ScheduledTaskInfo
Write-Host "Tarea 'Aula Meteo' registrada. Próxima ejecución: $($info.NextRunTime)"
