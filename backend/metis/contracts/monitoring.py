from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from metis.contracts.base import ContractModel
from metis.contracts.header import MessageHeader


class MonitorPublishHeader(MessageHeader):
    type: Literal["monitor_publish"] = "monitor_publish"


class MonitorSample(ContractModel):
    device_id: str = Field(min_length=1)
    monitor: str = Field(min_length=1)
    acquired_at: datetime
    value: dict[str, Any]


class MonitorPublish(ContractModel):
    header: MonitorPublishHeader
    payload: MonitorSample