# backend/src/metis/contracts/registration.py

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RegistrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OperationDescription(RegistrationModel):
    """agent が提供する操作のスキーマ。"""

    request_schema: dict[str, Any]
    result_schema: dict[str, Any]


class MonitorDescription(RegistrationModel):
    """agent が提供する監視値のスキーマ。"""

    state_schema: dict[str, Any]


class AgentDescription(RegistrationModel):
    """agent の識別情報と提供機能。"""

    agent_id: str = Field(min_length=1)
    device_type: str = Field(min_length=1)

    operations: dict[str, OperationDescription] = Field(
        default_factory=dict,
    )
    monitors: dict[str, MonitorDescription] = Field(
        default_factory=dict,
    )


class RegisterAgentRequest(RegistrationModel):
    """WebSocket 接続後に agent が送る登録メッセージ。"""

    type: Literal["register_agent"] = "register_agent"
    agent: AgentDescription


class RegisterAgentAccepted(RegistrationModel):
    """central が登録を受け付けた応答。"""

    type: Literal["register_agent_accepted"] = "register_agent_accepted"
    agent_id: str = Field(min_length=1)
