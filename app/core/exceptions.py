"""自定义异常类"""


class TaskLoadError(Exception):
    """任务加载异常"""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception
