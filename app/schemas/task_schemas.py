from typing import Any

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """任务请求模型"""

    flow: str = Field(..., description="任务所属流程/目录,如 'demo'")
    task: str = Field(..., description="任务名称,如 'read_excel'")
    data: dict[str, Any] = Field(
        default_factory=dict, description="传递给任务的业务数据"
    )


class TaskResponse(BaseModel):
    task_id: str
    flow: str
    task: str
    status: str
    result: dict[str, Any] = {}
    duration_ms: int = 0
