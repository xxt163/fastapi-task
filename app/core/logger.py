"""日志模块"""

import json
import logging
import os
from datetime import datetime, timezone

from app.core.config import settings

LOG_DIR = os.path.join(settings.project_root_dir, "logs")


class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "error"):
            log_data["error"] = record.error
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def _get_log_level() -> int:
    level = getattr(settings, "log_level", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _build_logger(name: str, file_path: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(_get_log_level())

    abs_path = os.path.abspath(file_path)
    for handler in logger.handlers[:]:
        if (
            hasattr(handler, "baseFilename")
            and os.path.abspath(handler.baseFilename) == abs_path
        ):
            return logger
        handler.close()
        logger.removeHandler(handler)

    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger


def get_service_logger(name: str = "service") -> logging.Logger:
    """
    获取服务级日志记录器

    日志文件: {LOG_DIR}/{date}/{name}.log
    按天分目录，同一天追加写入
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = os.path.join(LOG_DIR, date_str)
    _ensure_dir(date_dir)
    file_path = os.path.join(date_dir, f"{name}.log")
    return _build_logger(f"service.{name}", file_path)


def get_task_logger(flow: str, task: str) -> logging.Logger:
    """
    获取任务级日志记录器

    日志文件: {LOG_DIR}/{date}/{flow}/{task}-{timestamp}.log
    每次执行创建新文件
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H%M%S")
    date_dir = os.path.join(LOG_DIR, date_str, flow)
    _ensure_dir(date_dir)
    file_path = os.path.join(date_dir, f"{task}-{timestamp}.log")
    return _build_logger(f"tasks.{flow}.{task}", file_path)
