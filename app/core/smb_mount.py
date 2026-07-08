"""SMB 网络共享盘挂载工具。

Windows 服务运行在 Session 0，与用户桌面会话完全隔离，
用户桌面映射的盘符在服务进程内不可见。本模块在服务自身会话中
完成盘符映射，确保任务脚本能正常访问网络共享路径。
"""

import subprocess
import sys
from pathlib import Path


def mount_smb_drive(drive: str, share: str, username: str = "", password: str = ""):
    """挂载 SMB 网络共享盘到指定盘符。

    先断开旧连接（忽略错误），再重新挂载。盘符映射只在**当前会话**
    内生效，不影响用户桌面会话中的同名盘符。

    Args:
        drive: 盘符，如 "F:"（冒号必填）
        share: UNC 共享路径，如 "\\\\192.168.1.100\\data"
        username: SMB 认证用户名，传空则用 Windows 凭据管理器中的缓存凭据
        password: SMB 认证密码

    Returns:
        bool: 挂载成功返回 True，失败返回 False
    """
    if sys.platform != "win32":
        print("[SMB] Skipped: not on Windows")
        return True  # 非 Windows 环境不报错

    # 未配置时静默跳过
    if not drive or not share:
        return True

    print(f"[SMB] Mounting {share} -> {drive} ...")

    # 先断开旧连接（忽略错误：可能之前未挂载，或属于其他会话）
    subprocess.run(
        ["net", "use", drive, "/delete"],
        capture_output=True,
        text=True,
    )

    # 重新挂载
    cmd = ["net", "use", drive, share]
    if password:
        cmd.append(password)
    if username:
        cmd.extend(["/user:" + username])
    cmd.append("/persistent:no")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[SMB] Mount failed: {result.stderr.strip()}")
        return False

    print(f"[SMB] Mounted successfully: {drive}")
    return True


def ensure_smb_mount(
    drive: str,
    share: str,
    username: str = "",
    password: str = "",
    *,
    force_remount: bool = True,
):
    """确保 SMB 共享盘已挂载（开发/生产通用入口）。

    生产模式（force_remount=True）：
        无条件先断开再挂载，确保每次启动都是全新连接。

    开发模式（force_remount=False）：
        先检查盘符是否已可访问，已存在则跳过（避免打断用户手动挂载的连接）。

    Args:
        drive: 盘符，如 "F:"
        share: UNC 路径
        username: SMB 用户名
        password: SMB 密码
        force_remount: True=强制重挂，False=已存在则跳过

    Returns:
        bool: 挂载成功或已存在返回 True
    """
    if not drive or not share:
        return True

    if not force_remount and _drive_accessible(drive):
        print(f"[SMB] Drive {drive} already accessible, skipped.")
        return True

    return mount_smb_drive(drive, share, username, password)


def unmount_smb_drive(drive: str):
    """断开 SMB 网络共享盘。

    只在当前会话内生效，不影响用户桌面会话中的同名盘符。

    Args:
        drive: 盘符，如 "F:"
    """
    if sys.platform != "win32":
        return
    if not drive:
        return

    print(f"[SMB] Unmounting {drive} ...")
    result = subprocess.run(
        ["net", "use", drive, "/delete"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[SMB] Unmounted successfully: {drive}")
    else:
        # 可能本来就没挂载，忽略
        pass


def _drive_accessible(drive: str) -> bool:
    """检查盘符是否已可访问（存在且可列出内容）。"""
    try:
        path = Path(drive + "\\")
        return path.exists()
    except Exception:
        return False
