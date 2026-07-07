from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import get_service_logger
from app.api.task import router as task_router
from app.api.health import router as health_router

logger = get_service_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Service starting", extra={"host": settings.app_host, "port": settings.app_port})
    yield
    logger.info("Service stopped")


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(task_router)