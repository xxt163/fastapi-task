import os

# 开发模式强制开启 DEBUG，使任务模块在热重载后重新加载
os.environ["DEBUG"] = "true"

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        reload_dirs=["app", "tasks"],
    )
