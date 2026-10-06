from typing import Any, Literal

from pydantic import Field

from .base import ContractModel
from .header import MessageHeader


class AgentRegisterHeader(MessageHeader):
    type: Literal["agent_register"] = "agent_register"


class AgentRegisterPayload(ContractModel):
    """GenericAgent.describe() の内容。"""

    agent_id: str = Field(min_length=1)
    device_type: str = Field(min_length=1)

    operations: dict[str, dict[str, Any]]
    monitors: dict[str, dict[str, Any]]


class AgentRegister(ContractModel):
    header: AgentRegisterHeader
    payload: AgentRegisterPayload


class AgentRegisteredHeader(MessageHeader):
    type: Literal["agent_registered"] = "agent_registered"


class AgentRegisteredPayload(ContractModel):
    agent_id: str = Field(min_length=1)


class AgentRegistered(ContractModel):
    header: AgentRegisteredHeader
    payload: AgentRegisteredPayload