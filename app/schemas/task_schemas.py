import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

# 预编译正则表达式模式（只匹配小写，因为会自动转小写）
FLOW_PATTERN = re.compile(r"^[a-z][a-z0-9]*$")
TASK_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class TaskRequest(BaseModel):
    """任务请求模型"""

    flow: str = Field(..., description="任务所属流程/目录,如 'demo'")
    task: str = Field(..., description="任务名称,如 'read_excel'")
    data: dict[str, Any] = Field(
        default_factory=dict, description="传递给任务的业务数据"
    )

    @field_validator("flow")
    @classmethod
    def validate_flow(cls, v: str) -> str:
        """验证 flow 参数：必须以字母开头，只能包含字母和数字，自动转小写"""
        v = v.lower()

        # 验证格式：必须以字母开头，只能包含字母和数字
        if not FLOW_PATTERN.match(v):
            raise ValueError(
                "Invalid flow: must start with a letter and contain only letters and digits"
            )

        return v

    @field_validator("task")
    @classmethod
    def validate_task(cls, v: str) -> str:
        """验证 task 参数：必须以字母开头，可以包含字母、数字和下划线，自动转小写"""
        v = v.lower()

        # 验证格式：必须以字母开头，可以包含字母、数字和下划线
        if not TASK_PATTERN.match(v):
            raise ValueError(
                "Invalid task: must start with a letter and contain only letters, digits, and underscores"
            )

        return v


class TaskResponse(BaseModel):
    task_id: str
    flow: str
    task: str
    status: str
    result: Any = None
    error: str | None = None
    duration_ms: int = 0
