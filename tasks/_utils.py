"""tasks 包共享工具 —— 日志获取 + 本地调试入口"""

import logging
from typing import Any, Callable


def get_logger(name: str | None = None) -> logging.Logger:
    """返回 INFO 级别的 logger，替代每个 task 文件顶部的样板代码"""
    logger = logging.getLogger(name or __name__)
    logger.setLevel(logging.INFO)
    return logger


def run_main(run_func: Callable[[dict], Any], params: dict) -> None:
    """if __name__ == '__main__' 的统一入口，配置 StreamHandler 后执行 run"""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    )
    # 挂到 root logger，确保所有子 logger 的输出都可见
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    print(run_func(params))