# 註冊 Windows 工作排程：交易日每小時執行盤中監控
# 用法（一般權限即可，免系統管理員）：
#   powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
# 移除：
#   powershell -ExecutionPolicy Bypass -File setup_schedule.ps1 -Remove

param([switch]$Remove)

$TaskName = "TW_AI_StockMonitor"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Python = (Get-Command python).Source
$Target = Join-Path $ScriptDir "hourly_monitor.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已移除排程：$TaskName"
    return
}

# 動作：執行監控腳本（腳本內會自行判斷是否盤中）
$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Target`"" -WorkingDirectory $ScriptDir

# 觸發：週一至週五 09:00 起，每小時重複一次，持續 5 小時（涵蓋 09:00~13:30）
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 9:00AM
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At 9:00AM `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Hours 5)).Repetition

$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Description "台股 AI 產業盤中每小時監控" -Force | Out-Null

Write-Host "✅ 已建立排程：$TaskName"
Write-Host "   交易日 09:00-14:00 每小時執行一次（非盤中自動跳過）"
Write-Host "   立即測試：Start-ScheduledTask -TaskName $TaskName"
Write-Host "   查看狀態：Get-ScheduledTask -TaskName $TaskName"
Write-Host "   移除排程：powershell -ExecutionPolicy Bypass -File setup_schedule.ps1 -Remove"
