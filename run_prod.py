import sys

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
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
        log_config=None,
    )
