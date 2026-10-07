$ErrorActionPreference = 'Stop'
$taskName = 'DailyCodeAgent'
$projectDir = $PSScriptRoot
$runFile = Join-Path $projectDir 'RUN.cmd'
if (-not (Test-Path -LiteralPath $runFile -PathType Leaf)) { throw "RUN.cmd topilmadi: $runFile" }
$command = "set DAILYCODE_SCHEDULED=1&& call `"$runFile`""
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/d /c $command" -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Daily -At '09:23'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Har kuni yetti tilda oquv kodi yaratadi' -Force | Out-Null
Write-Host "Tayyor: '$taskName' har kuni mahalliy vaqt bilan 09:23 ga o'rnatildi."
Write-Host "Tekshirish: Task Scheduler > Task Scheduler Library > $taskName"
