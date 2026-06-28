import importlib


def load_task(flow: str, task: str):
    """
    动态加载任务模块并返回 run 函数
    """
    module_path = f"tasks.{flow}.{task}"

    try:
        module = importlib.import_module(module_path)
        run_func = getattr(module, "run")
    except ImportError:
        raise ImportError(f"无法导入任务模块: {module_path}")
    except AttributeError:
        raise AttributeError(f"任务模块 {module_path} 没有 run 函数")
    return run_func
