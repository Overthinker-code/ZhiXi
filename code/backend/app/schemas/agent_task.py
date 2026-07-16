from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


AgentTaskStatus = Literal["waiting", "running", "completed", "failed"]


class AgentTaskPublic(BaseModel):
    id: int
    session_id: str
    run_id: str
    task_key: str
    agent_name: str
    status: AgentTaskStatus
    progress: int
    message: str
    created_time: datetime
    updated_time: datetime

    model_config = ConfigDict(from_attributes=True)
