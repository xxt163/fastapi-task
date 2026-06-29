# ============================================================
# Windows 服务删除脚本 (使用 nssm)
# 用法: 直接运行 .\remove_service.ps1，脚本会自动提权
# ============================================================

# ---------- 自动提权 (非管理员时重新以管理员身份启动) ----------
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting Administrator privileges..."
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    Start-Process PowerShell.exe -Verb RunAs -ArgumentList $args
    exit
}

# ---------- 可修改的配置 ----------

# 服务名称 (与 create_service.ps1 中保持一致)
$ServiceName = "FastAPITask"

# ---------- 以下一般不需要修改 ----------

$NssmExe = Join-Path $PSScriptRoot "nssm.exe"

if (-not (Test-Path $NssmExe)) {
    Write-Error "nssm.exe not found: $NssmExe"
    exit 1
}

# 删除每天定时重启的计划任务
$TaskName = "${ServiceName}_DailyRestart"
Write-Host "Removing scheduled task '$TaskName'..."
schtasks /delete /tn $TaskName /f 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Scheduled task removed."
} else {
    Write-Host "Scheduled task not found, skip."
}

# 检查服务是否存在
$existing = & $NssmExe status $ServiceName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Service '$ServiceName' does not exist, nothing to remove."
    exit 0
}

# 停止服务
Write-Host "Stopping service '$ServiceName'..."
& $NssmExe stop $ServiceName 2>$null

# 删除服务
Write-Host "Removing service '$ServiceName'..."
& $NssmExe remove $ServiceName confirm 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to remove service."
    exit 1
}

Write-Host "Service '$ServiceName' removed successfully."
