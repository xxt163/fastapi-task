import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import get_service_logger
from app.api.task import router as task_router
from app.api.health import router as health_router

logger = get_service_logger("startup")
_effective_drive: str | None = None


def _delete_network_drive(drive: str) -> None:
    if not drive:
        return
    try:
        subprocess.run(
            ["net", "use", drive, "/delete", "/y"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.CalledProcessError:
        pass


def _connect_network_drive() -> None:
    """服务启动时挂载网络驱动器"""
    global _effective_drive

    remote = settings.net_share_remote
    drive = settings.net_share_drive or remote
    user = settings.net_share_user
    password = settings.net_share_password

    if not remote:
        return

    _delete_network_drive(drive)
    _effective_drive = drive

    cmd = ["net", "use", drive, remote, "/persistent:no"]
    if user:
        cmd.append(f"/user:{user}")
    if password:
        cmd.append(password)

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        logger.info("Network drive mounted", extra={"drive": drive, "remote": remote})
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or e.stdout or str(e)).strip()
        logger.error(
            "Network drive mount failed",
            extra={"drive": drive, "remote": remote, "error": stderr},
        )


def _disconnect_network_drive() -> None:
    """服务停止时断开网络驱动器"""
    global _effective_drive

    drive = _effective_drive or settings.net_share_drive
    if not drive:
        return

    _delete_network_drive(drive)
    logger.info("Network drive disconnected", extra={"drive": drive})
    _effective_drive = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    _connect_network_drive()
    yield
    _disconnect_network_drive()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(task_router)
