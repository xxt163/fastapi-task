import asyncio
import time
import traceback
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks

from app.core.logger import get_task_logger
from app.schemas.task_schemas import TaskRequest, TaskResponse
from app.services.email import send_task_failure_email
from app.services.task_loader import load_task, get_task_list

router = APIRouter(prefix="/task", tags=["Tasks"])


@router.get("/list", summary="Get all tasks")
async def get_tasks():
    """
    Retrieve a list of all tasks.
    """
    return {"tasks": get_task_list()}


@router.post("/run", summary="Run a task")
async def run_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Run a task.
    """
    task_id = str(uuid4())
    start_time = time.perf_counter()
    status = "success"
    result = None
    error_message = None

    # 获取任务日志记录器
    logger = get_task_logger(request.flow, request.task)
    logger.info("Task started", extra={"task_id": task_id})

    try:
        task_run_func = load_task(request.flow, request.task)
        result = await asyncio.to_thread(task_run_func, request.data)
    except Exception:
        status = "failed"
        error_message = traceback.format_exc()
        logger.error("Task failed", extra={"task_id": task_id, "error": error_message})
        failure_duration_ms = int((time.perf_counter() - start_time) * 1000)
        background_tasks.add_task(
            send_task_failure_email,
            task_id,
            request.flow,
            request.task,
            error_message,
            failure_duration_ms,
        )

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    if status == "success":
        logger.info(
            "Task completed", extra={"task_id": task_id, "duration_ms": duration_ms}
        )

    return TaskResponse(
        task_id=task_id,
        flow=request.flow,
        task=request.task,
        status=status,
        result=result,
        error=error_message,
        duration_ms=duration_ms,
    )
