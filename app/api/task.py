import asyncio
import contextlib
import io
import sys
import time
import traceback
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.encoders import jsonable_encoder

from app.core.config import settings
from app.core.logger import get_task_logger
from app.schemas.task_schemas import TaskRequest, TaskResponse
from app.services.email import send_task_failure_email
from app.services.task_loader import load_task, get_task_list

router = APIRouter(prefix="/task", tags=["Tasks"])

# 并发控制信号量，限制同时执行的任务数量
_semaphore = asyncio.Semaphore(settings.task_max_concurrency)


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
                try:
                    self._logger.info(stripped)
                except Exception:
                    print(
                        f"[_PrintToLogger] logger failed, fallback: {stripped}",
                        file=sys.stderr,
                    )
        return len(s)

    def flush(self) -> None:
        if self._buffer.strip():
            try:
                self._logger.info(self._buffer.strip())
            except Exception:
                # logger 写入失败时不丢内容，回退到 stderr
                print(
                    f"[_PrintToLogger] logger failed, fallback: {self._buffer.strip()}",
                    file=sys.stderr,
                )
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
    # 并发控制：超过限制时返回 503 而非无限排队
    if _semaphore.locked():
        raise HTTPException(
            status_code=503,
            detail=f"Server busy: max {settings.task_max_concurrency} concurrent tasks. Retry later.",
        )

    async with _semaphore:
        task_id = str(uuid4())
        start_time = time.perf_counter()
        status = "success"
        result = None
        error_message = None

        logger = get_task_logger(task_id, request.flow, request.task)
        logger.info("Task started", extra={"task_id": task_id})

        try:
            task_run_func = load_task(request.flow, request.task)
            capture = _PrintToLogger(logger)
            with contextlib.redirect_stdout(capture):
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(task_run_func, request.data),
                        timeout=settings.task_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"Task timed out after {settings.task_timeout_seconds}s "
                        f"(thread continues in background)"
                    )
                finally:
                    capture.flush()
        except Exception as e:
            status = "failed"
            # traceback.format_exc() 最后一行已包含异常消息，无需再拼接 str(e)
            error_message = traceback.format_exc()
            logger.error(
                "Task failed", extra={"task_id": task_id, "error": error_message}
            )
            failure_duration_ms = int((time.perf_counter() - start_time) * 1000)
            background_tasks.add_task(
                send_task_failure_email,
                task_id,
                request.flow,
                request.task,
                error_message,
                failure_duration_ms,
            )
        finally:
            # 关闭日志 handler 释放文件描述符
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

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
