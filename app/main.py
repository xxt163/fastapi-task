from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import get_service_logger, setup_root_logger
from app.core.smb_mount import ensure_smb_mount, unmount_smb_drive
from app.api.task import router as task_router
from app.api.health import router as health_router

setup_root_logger()

logger = get_service_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时挂载 SMB 网络共享盘（服务运行在 Session 0，需在本会话内挂载）
    # 生产模式强制重挂；开发模式已存在则跳过，避免热重载打断用户手动挂载
    ensure_smb_mount(
        drive=settings.smb_drive_letter,
        share=settings.smb_share_path,
        username=settings.smb_username,
        password=settings.smb_password,
        force_remount=not settings.debug,
    )
    logger.info("Service starting", extra={"host": settings.app_host, "port": settings.app_port})
    yield
    # 停止时断开 SMB 连接
    logger.info("Service stopped")
    unmount_smb_drive(settings.smb_drive_letter)


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(task_router)
