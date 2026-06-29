"""日志模块"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

# 日志目录
LOG_DIR = Path(settings.project_root_dir) / "logs"


class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # 添加 extra 字段
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "error"):
            log_data["error"] = record.error
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # 添加异常信息
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def _get_log_level() -> int:
    """获取日志级别"""
    level = getattr(settings, "log_level", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def get_service_logger() -> logging.Logger:
    """
    获取服务级日志记录器

    日志路径: {LOG_DIR}/{date}/service.log
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = LOG_DIR / date_str
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("service")
    logger.setLevel(_get_log_level())

    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "service.log", encoding="utf-8")
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


def get_task_logger(flow: str, task: str) -> logging.Logger:
    """
    获取任务级日志记录器

    日志路径: {LOG_DIR}/{date}/{flow}/{task}-{timestamp}.log

    Args:
        flow: 流程名称
        task: 任务名称
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H%M%S")
    log_dir = LOG_DIR / date_str / flow
    log_dir.mkdir(parents=True, exist_ok=True)

    logger_name = f"tasks.{flow}.{task}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(_get_log_level())

    # 每次执行创建新文件
    log_file = log_dir / f"{task}-{timestamp}.log"

    # 清除旧处理器，避免重复
    logger.handlers.clear()

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger
