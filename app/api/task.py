import asyncio
import time
import traceback
from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import get_task_logger
from app.schemas.task_schemas import TaskRequest, TaskResponse
from app.services.email import send_task_failure_email
from app.services.task_loader import load_task

router = APIRouter(prefix="/task", tags=["Tasks"])


# 任务模块根目录
_TASKS_DIR = Path(settings.project_root_dir) / "tasks"


@router.get("/list", summary="Get all tasks")
async def get_tasks():
    """
    Retrieve a list of all tasks.
    """
    # 如果任务目录不存在,返回空列表
    if not _TASKS_DIR.exists():
        return {"tasks": []}

    # 使用列表推导式遍历任务目录,收集所有有效的任务
    tasks = [
        {
            "flow": flow_dir.name,
            "task": task_file.stem,
            "path": str(task_file.relative_to(_TASKS_DIR.parent)),
        }
        for flow_dir in sorted(_TASKS_DIR.iterdir())
        # 只处理目录,并排除以 "_" 或 "." 开头的隐藏/特殊目录
        if flow_dir.is_dir() and not flow_dir.name.startswith(("_", "."))
        for task_file in sorted(flow_dir.glob("*.py"))
        # 排除以 "_" 开头的 Python 文件
        if not task_file.name.startswith("_")
    ]

    return {"tasks": tasks}


@router.post("/run", summary="Run a task")
async def run_task(request: TaskRequest):
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
        # 加载指定任务的 run 函数
        task_run_func = load_task(request.flow, request.task)
        # 执行任务
        result = await asyncio.to_thread(task_run_func, request.data)
    except Exception as e:
        # 捕获任务执行异常,记录完整堆栈信息
        status = "failed"
        error_message = traceback.format_exc() + "\nError: " + str(e)
        logger.error("Task failed", extra={"task_id": task_id, "error": error_message})
        asyncio.create_task(
            send_task_failure_email(
                task_id, request.flow, request.task, error_message, duration_ms
            )
        )

    # 计算耗时(毫秒)
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
        result=result if error_message is None else {"error": error_message},
        duration_ms=duration_ms,
    )
