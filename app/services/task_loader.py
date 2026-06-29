"""任务模块加载器"""

import importlib
from typing import Any, Callable

from app.core.exceptions import TaskLoadError


_module_cache: dict[str, Any] = {}


def clear_module_cache() -> None:
    """清除模块缓存，用于开发热重载"""
    _module_cache.clear()


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
