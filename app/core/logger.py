"""日志模块"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from app.core.config import settings

CST = timezone(timedelta(hours=8))  # 中国标准时间 UTC+8

LOG_DIR = os.path.join(settings.project_root_dir, "logs")

# LogRecord 标准属性，extra 字段过滤时排除
_STANDARD_RECORD_ATTRS = frozenset(
    [
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    ]
)


class JSONFormatter(logging.Formatter):
    """JSON 格式日志，extra 传入的字段自动输出到 JSON"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": datetime.now(CST).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # 通用 extra 字段：所有非 LogRecord 标准属性自动输出
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_")
        }
        log_data.update(extra_fields)

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def _get_log_level() -> int:
    level = getattr(settings, "log_level", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


class _DateRotatingFileHandler(logging.Handler):
    """按日期自动切换文件的日志 handler。

    每次 emit 时根据当前日期决定文件路径：
    - logs/2026-07-08/{name}.log
    跨午夜后自动写入新日期的文件，旧文件句柄自动关闭。
    """

    def __init__(self, name: str, encoding: str = "utf-8"):
        super().__init__()
        self._name = name
        self._encoding = encoding
        self._current_path: str = ""
        self._file = None

    def emit(self, record: logging.LogRecord) -> None:
        try:
            date_str = datetime.now(CST).strftime("%Y-%m-%d")
            date_dir = os.path.join(LOG_DIR, date_str)
            file_path = os.path.join(date_dir, f"{self._name}.log")

            if file_path != self._current_path:
                _ensure_dir(date_dir)
                if self._file:
                    self._file.close()
                self._file = open(  # noqa: SIM115
                    file_path, "a", encoding=self._encoding
                )
                self._current_path = file_path

            self._file.write(self.format(record) + "\n")
            self._file.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
        super().close()


def get_service_logger(name: str = "service") -> logging.Logger:
    """获取服务级日志记录器。

    日志文件: {LOG_DIR}/{date}/{name}.log
    自动按天切换，跨午夜后写入新日期的文件。
    """
    logger = logging.getLogger(f"service.{name}")
    logger.setLevel(_get_log_level())
    logger.propagate = False

    # 清除旧 handler（如模块热重载导致重复添加）
    for h in logger.handlers[:]:
        if isinstance(h, _DateRotatingFileHandler) and h._name == name:
            return logger
        h.close()
        logger.removeHandler(h)

    handler = _DateRotatingFileHandler(name)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger


def get_task_logger(task_id: str, flow: str, task: str) -> logging.Logger:
    """获取任务级日志记录器，每次执行独立。

    日志文件: {LOG_DIR}/{date}/{flow}/{task}-{HHMMSS}-{task_id前8位}.log
    每次执行创建新文件，task_id 确保并发调用不串日志。
    """
    date_str = datetime.now(CST).strftime("%Y-%m-%d")
    timestamp = datetime.now(CST).strftime("%H%M%S")
    date_dir = os.path.join(LOG_DIR, date_str, flow)
    _ensure_dir(date_dir)
    short_id = task_id[:8]
    file_path = os.path.join(date_dir, f"{task}-{timestamp}-{short_id}.log")

    # task_id 唯一化 logger name，避免并发请求共享 logger 导致 handler 累积
    logger = logging.getLogger(f"tasks.{flow}.{task}.{short_id}")
    logger.setLevel(_get_log_level())
    logger.propagate = False

    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger


def get_uvicorn_log_config() -> dict:
    """生成 uvicorn 日志配置，使用日期感知 handler 写入 JSON 文件。"""
    log_level = _get_log_level()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "app.core.logger.JSONFormatter",
            },
        },
        "handlers": {
            "access": {
                "()": "app.core.logger._DateRotatingFileHandler",
                "name": "access",
                "encoding": "utf-8",
                "formatter": "json",
            },
            "uvicorn": {
                "()": "app.core.logger._DateRotatingFileHandler",
                "name": "uvicorn",
                "encoding": "utf-8",
                "formatter": "json",
            },
        },
        "loggers": {
            "uvicorn.access": {
                "handlers": ["access"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["uvicorn"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.asgi": {
                "handlers": ["uvicorn"],
                "level": log_level,
                "propagate": False,
            },
        },
    }


def setup_root_logger() -> None:
    """配置 root logger，兜底捕获未路由到文件的日志。

    任务脚本的 print() 在服务模式下由 _PrintToLogger 劫持写入 JSON 日志，
    此处配置 root logger → stderr 作为兜底，确保日志不会静默丢失。
    """
    root = logging.getLogger()
    root.setLevel(_get_log_level())

    # 避免重复添加
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
