import sys

import uvicorn

from app.core.config import settings
from app.core.logger import get_uvicorn_log_config
from app.core.smb_mount import ensure_smb_mount


if __name__ == "__main__":
    # Windows 服务运行在 Session 0，需在服务自身会话中挂载 SMB 盘符。
    # 生产模式强制重挂（force_remount=True），确保每次启动都是全新连接。
    ensure_smb_mount(
        drive=settings.smb_drive_letter,
        share=settings.smb_share_path,
        username=settings.smb_username,
        password=settings.smb_password,
        force_remount=True,
    )

    workers = settings.workers
    if sys.platform == "win32" and workers > 1:
        print(
            f"Warning: WORKERS={workers} is not supported on Windows, using 1 instead."
        )
        workers = 1

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=workers,
        log_config=get_uvicorn_log_config(),
    )
