# ============================================================
# Windows 服务创建脚本 (使用 nssm)
# 用法: 直接运行 .\create_service.ps1，脚本会自动提权
# ============================================================

# ---------- 自动提权 (非管理员时重新以管理员身份启动) ----------
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting Administrator privileges..."
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    Start-Process PowerShell.exe -Verb RunAs -ArgumentList $args
    exit
}

# ---------- 自动获取路径 ----------

# 项目根目录 (scripts 的上级目录)
$ProjectRoot = (Get-Item "$PSScriptRoot\..").FullName

# 自动拼接 .venv 虚拟环境中的 Python 路径
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# ---------- 可修改的配置 ----------

# 服务名称 (在 services.msc 中显示的名称)
$ServiceName = "FastAPITask"

# 服务描述
$ServiceDescription = "FastAPI Task 任务调度服务"

# Python 解释器路径 (默认自动使用项目目录下的 .venv)
# - 使用 .venv (默认):   $VenvPython
# - 使用 uv:             "uv"
# - 系统 Python:         "python" 或 "C:\Python310\python.exe"
$PythonExe = $VenvPython

# Python 解释器的额外启动参数
# - 用 python 时留空:  @()
# - 用 uv 时填:        @("run")
$PythonArgs = @()

# 启动脚本 (相对于项目根目录)
$StartScript = "run_prod.py"

# 每天定时重启 (通过 Windows 计划任务实现)
# - 设为 $null 则不启用:  $DailyRestartTime = $null
# - 设为 "HH:MM" 格式启用: $DailyRestartTime = "03:00"
$DailyRestartTime = "01:00"

# ---------- 以下一般不需要修改 ----------

# nssm.exe 路径
$NssmExe = Join-Path $PSScriptRoot "nssm.exe"

if (-not (Test-Path $NssmExe)) {
    Write-Error "nssm.exe not found: $NssmExe"
    exit 1
}

$StartScriptPath = Join-Path $ProjectRoot $StartScript
if (-not (Test-Path $StartScriptPath)) {
    Write-Error "Start script not found: $StartScriptPath"
    exit 1
}

Write-Host "============================================"
Write-Host "  Installing Windows Service: $ServiceName"
Write-Host "============================================"
Write-Host "Project Root:  $ProjectRoot"
Write-Host "Python Exe:    $PythonExe"
Write-Host "Python Args:   $($PythonArgs -join ' ')"
Write-Host "Start Script:  $StartScriptPath"
if ($DailyRestartTime) {
    Write-Host "Daily Restart: $DailyRestartTime"
}
Write-Host ""

# 构造 nssm install 参数
$NssmArgs = @("install", $ServiceName, $PythonExe)
if ($PythonArgs.Count -gt 0) {
    $NssmArgs += $PythonArgs
}
$NssmArgs += $StartScriptPath

# 停止并删除已有服务
$existing = & $NssmExe status $ServiceName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Service already exists, stopping and removing..."
    & $NssmExe stop $ServiceName 2>$null
    & $NssmExe remove $ServiceName confirm 2>$null

    # 同时删除旧计划任务
    $TaskName = "${ServiceName}_DailyRestart"
    schtasks /delete /tn $TaskName /f 2>$null
    Write-Host "Old service removed."
}

# 安装服务
Write-Host "Creating service..."
$result = & $NssmExe $NssmArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install service!"
    Write-Host $result
    exit 1
}

# 验证
$check = & $NssmExe status $ServiceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Service was not created: $check"
    exit 1
}
Write-Host "Service created successfully."

# 配置服务
Write-Host "Configuring service..."
& $NssmExe set $ServiceName AppDirectory $ProjectRoot 2>$null
& $NssmExe set $ServiceName Description $ServiceDescription 2>$null
& $NssmExe set $ServiceName Start SERVICE_AUTO_START 2>$null
& $NssmExe set $ServiceName AppExit Default Restart 2>$null

# 启动服务
Write-Host "Starting service..."
& $NssmExe start $ServiceName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start service."
    Write-Host ""
    Write-Host "Check Windows Event Viewer for details, or run:"
    Write-Host "  nssm status $ServiceName"
    Write-Host "  nssm remove $ServiceName confirm"
    exit 1
}

# 创建每天定时重启的计划任务
if ($DailyRestartTime) {
    $TaskName = "${ServiceName}_DailyRestart"
    $ScheduleCmd = "nssm restart $ServiceName"
    Write-Host "Creating daily restart task at $DailyRestartTime..."
    schtasks /create /tn $TaskName /tr "$ScheduleCmd" /sc daily /st $DailyRestartTime /ru SYSTEM /f 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Daily restart task created successfully."
    } else {
        Write-Host "Warning: Failed to create daily restart task."
    }
}

Write-Host ""
Write-Host "============================================"
Write-Host "  Service installed successfully!"
Write-Host "  Name:   $ServiceName"
Write-Host "  Status: Running"
Write-Host "============================================"
Write-Host ""
Write-Host "Management commands:"
Write-Host "  Check status:  nssm status $ServiceName"
Write-Host "  Stop:          nssm stop $ServiceName"
Write-Host "  Start:         nssm start $ServiceName"
Write-Host "  Restart:       nssm restart $ServiceName"
Write-Host "  Remove:        .\remove_service.ps1"
