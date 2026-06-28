from fastapi import FastAPI

from app.core.config import settings

from app.api.task import router as task_router
from app.api.health import router as health_router

app = FastAPI(title=settings.app_name, debug=settings.debug)


app.include_router(health_router)  # Include the health check router
app.include_router(task_router)  # Include the task router
