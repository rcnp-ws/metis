# backend/src/metis/contracts/monitoring.py

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from metis.contracts.base import ContractModel


class MonitorSample(ContractModel):
    """ある機器の監視値を取得した結果。"""

    device_id: str = Field(
        min_length=1,
        description="監視対象の機器",
    )
    monitor: str = Field(
        min_length=1,
        description="Agentに登録された監視名",
    )
    acquired_at: datetime = Field(
        description="この監視値を取得した時刻",
    )
    value: dict[str, Any] = Field(
        description="機器固有モデルで検証した監視値",
    )


class MonitorPublish(ContractModel):
    """AgentからCentralへ送る監視値。"""

    type: Literal["monitor_publish"] = "monitor_publish"

    sent_at: datetime = Field(
        description="メッセージの送信開始直前の時刻",
    )
    payload: MonitorSample
