"""任务模块加载器"""

import importlib
from typing import Any, Callable


# 模块缓存
_module_cache: dict[str, Any] = {}


def get_task_module(flow: str, task: str) -> Any:
    """
    获取任务模块(带缓存)

    Args:
        flow: 流程名称
        task: 任务名称

    Returns:
        任务模块对象
    """
    module_name = f"tasks.{flow}.{task}"

    if module_name not in _module_cache:
        _module_cache[module_name] = importlib.import_module(module_name)

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
        AttributeError: 如果模块中没有 run 函数
    """
    module = get_task_module(flow, task)
    return getattr(module, "run")
