<#
.SYNOPSIS
  注册 Windows 任务计划，每天 11:00 执行 A股智能体概念监控

.DESCRIPTION
  注册一个 Windows 计划任务，每天上午 11:00 (北京时间) 触发，
  运行 stock_workflow 管线并输出日志。
#>

$TaskName = "AIAgentStockMonitor"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 系统上正确的 Python 路径（经检测 E:\python\python.exe 可用）
$PythonExe = "E:\python\python.exe"

if (-not (Test-Path $PythonExe)) {
    # Fallback: 从 PATH 中查找
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Host "错误: 未找到 Python，请确认已安装" -ForegroundColor Red
        exit 1
    }
}

$MainScript = Join-Path $ScriptDir "main.py"
$ConfigFile = Join-Path $ScriptDir "config.yaml"
$LogDir = Join-Path $ScriptDir "logs"

# 确保日志目录存在
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# 构建执行动作
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-c `"$ConfigFile`" -m once" `
    -WorkingDirectory $ScriptDir

# 触发器：每天 11:00
$Trigger = New-ScheduledTaskTrigger -Daily -At "11:00"

# 以当前用户运行
try {
    $Principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType S4U `
        -RunLevel Limited
} catch {
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
}

# 设置
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# 注册任务
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Force

    Write-Host "任务计划 [$TaskName] 已注册成功！" -ForegroundColor Green
    Write-Host "触发时间: 每天 11:00" -ForegroundColor Cyan
    Write-Host "工作目录: $ScriptDir" -ForegroundColor Cyan
    Write-Host "Python: $PythonExe" -ForegroundColor Cyan
    Write-Host "脚本: $MainScript" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "若要立即测试，请运行:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "若要删除任务，请运行:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "配置文件编辑: $ConfigFile" -ForegroundColor Yellow
    Write-Host "请先编辑 config.yaml 填入推送渠道的凭证。" -ForegroundColor Yellow
}
catch {
    Write-Host "注册失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "请尝试以管理员身份运行此脚本。" -ForegroundColor Yellow
    Write-Host "  powershell -Command `"Start-Process powershell -ArgumentList '-File \`"$PSCommandPath\`"' -Verb RunAs`"" -ForegroundColor Yellow
}
