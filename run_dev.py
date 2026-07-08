import os

# 开发模式强制开启 DEBUG，使任务模块在热重载后重新加载
os.environ["DEBUG"] = "true"

import uvicorn

from app.core.config import settings
from app.core.logger import get_uvicorn_log_config
from app.core.smb_mount import ensure_smb_mount


if __name__ == "__main__":
    # 开发模式：盘符已存在则跳过，避免打断用户手动挂载的连接
    ensure_smb_mount(
        drive=settings.smb_drive_letter,
        share=settings.smb_share_path,
        username=settings.smb_username,
        password=settings.smb_password,
        force_remount=False,
    )

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        reload_dirs=["app", "tasks"],
        log_config=get_uvicorn_log_config(),
    )
