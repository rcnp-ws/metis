# backend/src/metis/contracts/monitoring.py

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from metis.contracts.control import RejectionReason


class MonitoringModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MonitorRequest(MonitoringModel):
    """central から agent に送る監視値取得要求。"""

    type: Literal["monitor_request"] = "monitor_request"
    request_id: str = Field(min_length=1)
    monitor: str = Field(min_length=1)


class MonitorResult(MonitoringModel):
    """agent が返す現在の監視値。"""

    type: Literal["monitor_result"] = "monitor_result"
    request_id: str = Field(min_length=1)
    monitor: str = Field(min_length=1)
    state: dict[str, Any]


class MonitorFailed(MonitoringModel):
    """監視値を取得できなかった場合の応答。"""

    type: Literal["monitor_failed"] = "monitor_failed"
    request_id: str = Field(min_length=1)
    reason: RejectionReason
