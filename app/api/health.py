from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


def _check_drive(drive: str) -> bool:
    """检查盘符是否可访问（存在且可列出内容）。"""
    try:
        return Path(drive + "\\").exists()
    except Exception:
        return False


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint — verifies that the service and its dependencies are operational.

    Returns 200 with detailed status when healthy; 503 when a dependency is degraded.
    """
    checks: dict[str, str] = {}
    degraded: list[str] = []

    # 检查 tasks 目录是否可用
    tasks_dir = Path(settings.project_root_dir) / "tasks"
    if tasks_dir.is_dir():
        checks["tasks_dir"] = "ok"
    else:
        checks["tasks_dir"] = "missing"
        degraded.append("tasks_dir")

    # 如果配置了 SMB 共享盘，检查盘符是否可访问
    if settings.smb_drive_letter and settings.smb_share_path:
        if _check_drive(settings.smb_drive_letter):
            checks["smb_mount"] = "ok"
        else:
            checks["smb_mount"] = "degraded"
            degraded.append("smb_mount")

    status = "degraded" if degraded else "healthy"
    return {"status": status, "checks": checks}

