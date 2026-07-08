import asyncio
import contextlib
import io
import time
import traceback
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from fastapi.encoders import jsonable_encoder

from app.core.logger import get_task_logger
from app.schemas.task_schemas import TaskRequest, TaskResponse
from app.services.email import send_task_failure_email
from app.services.task_loader import load_task, get_task_list

router = APIRouter(prefix="/task", tags=["Tasks"])


class _PrintToLogger(io.TextIOBase):
    """将 task 脚本中的 print() 输出劫持到 JSON 日志。

    task 脚本只需用 print() 输出信息，无需任何 logger 导入。
    服务端自动将每行 print 输出转为 JSON 日志条目。
    """

    def __init__(self, logger):
        super().__init__()
        self._logger = logger
        self._buffer = ""

    def write(self, s: str) -> int:
        self._buffer += s
        lines = self._buffer.split("\n")
        self._buffer = lines.pop()  # 最后一个不完整行留着等下一条
        for line in lines:
            stripped = line.strip()
            if stripped:
                self._logger.info(stripped)
        return len(s)

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.info(self._buffer.strip())
            self._buffer = ""


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

    logger = get_task_logger(task_id, request.flow, request.task)
    logger.info("Task started", extra={"task_id": task_id})

    try:
        task_run_func = load_task(request.flow, request.task)
        # 劫持 stdout：task 脚本的 print() → task logger JSON 日志
        capture = _PrintToLogger(logger)
        with contextlib.redirect_stdout(capture):
            try:
                result = await asyncio.to_thread(task_run_func, request.data)
            finally:
                capture.flush()  # 确保异常时 buffer 中的内容也不丢
    except Exception as e:
        status = "failed"
        error_message = traceback.format_exc() + "\n\n" + str(e)
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
        result = jsonable_encoder(result)

    return TaskResponse(
        task_id=task_id,
        flow=request.flow,
        task=request.task,
        status=status,
        result=result,
        error=error_message,
        duration_ms=duration_ms,
    )
