"""任务模块加载器"""

import importlib
import time
from pathlib import Path
from typing import Any, Callable

from app.core.config import settings
from app.core.exceptions import TaskLoadError

_module_cache: dict[str, Any] = {}
_task_list_cache: dict[str, Any] = {}
_TASKS_DIR = Path(settings.project_root_dir) / "tasks"


def clear_module_cache() -> None:
    """清除模块缓存，用于开发热重载"""
    _module_cache.clear()
    _task_list_cache.clear()


def get_task_list() -> list[dict]:
    """
    获取所有任务列表（带 TTL 缓存）

    Returns:
        任务列表，每个元素包含 flow、task、path
    """
    now = time.time()
    cache = _task_list_cache.get("list")

    if cache and now - cache["timestamp"] < settings.task_list_cache_ttl:
        return cache["data"]

    if not _TASKS_DIR.exists():
        result = []
    else:
        result = [
            {
                "flow": flow_dir.name,
                "task": task_file.stem,
                "path": str(task_file.relative_to(_TASKS_DIR.parent)),
            }
            for flow_dir in sorted(_TASKS_DIR.iterdir())
            if flow_dir.is_dir() and not flow_dir.name.startswith(("_", "."))
            for task_file in sorted(flow_dir.glob("*.py"))
            if not task_file.name.startswith("_")
        ]

    _task_list_cache["list"] = {"timestamp": now, "data": result}
    return result


def get_task_module(flow: str, task: str) -> Any:
    """
    获取任务模块(带缓存)

    Args:
        flow: 流程名称
        task: 任务名称

    Returns:
        任务模块对象

    Raises:
        TaskLoadError: 如果模块不存在
    """
    module_name = f"tasks.{flow}.{task}"

    if module_name not in _module_cache:
        try:
            _module_cache[module_name] = importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            raise TaskLoadError(f"Task not found: {flow}/{task}", e)
        except ImportError as e:
            raise TaskLoadError(f"Task {flow}/{task} has import errors: {e}", e)

    return _module_cache[module_name]


def load_task(flow: str, task: str) -> Callable:
    """
    加载指定任务的 run 函数

    Args:
        flow: 流程名称
        task: 任务名称

    Returns:
        任务的 run 函数

    Raises:
        TaskLoadError: 如果模块不存在或没有 run 函数
    """
    module = get_task_module(flow, task)

    if not hasattr(module, "run"):
        raise TaskLoadError(f"Task {flow}/{task} has no 'run' function")

    run_func = getattr(module, "run")

    if not callable(run_func):
        raise TaskLoadError(f"'run' in {flow}/{task} is not callable")

    return run_func
