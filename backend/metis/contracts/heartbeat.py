# backend/src/metis/contracts/heartbeat.py

from datetime import datetime
from typing import Literal

from pydantic import Field

from metis.contracts.base import ContractModel
from metis.contracts.header import MessageHeader


class HeartbeatHeader(MessageHeader):
    """heartbeatのメッセージ種別を限定する。"""

    type: Literal["agent_heartbeat"] = "agent_heartbeat"


class HeartbeatPayload(ContractModel):
    """Agentが担当する機器の取得状態。"""

    acquiring: bool = Field(
        description="機器からの取得を継続しているか",
    )
    last_acquired_at: datetime | None = Field(
        description="最後に取得に成功した時刻。未取得ならNone",
    )


class AgentHeartbeat(ContractModel):
    """AgentからCentralへ送るheartbeat。"""
    header: HeartbeatHeader
    payload: HeartbeatPayload