# Register Windows Task Scheduler: daily briefing build at 20:00 (Beijing = local time)
$TaskName = 'WorldCupGame-DailyBriefing'
$Python = (Get-Command python).Source
$WorkDir = 'D:\AI\WorldCupGame'
$Script = Join-Path $WorkDir 'scripts\build_daily_briefing.py'
$Args = "`"$Script`" --upload"

$Action = New-ScheduledTaskAction -Execute $Python -Argument $Args -WorkingDirectory $WorkDir
$Trigger = New-ScheduledTaskTrigger -Daily -At '20:00'
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force `
    -Description 'Build daily WC briefing JSON and upload to PythonAnywhere'

Write-Host "Registered: $TaskName daily at 20:00"
Write-Host "Program: $Python"
Write-Host "Args: $Args"
