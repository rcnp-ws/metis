# backend/src/metis/contracts/alarm.py

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from metis.contracts.base import ContractModel
from metis.contracts.header import TrackableHeader


ContentT = TypeVar("ContentT", bound=BaseModel)


class AlarmPublishHeader(TrackableHeader):
    type: Literal["alarm_publish"] = "alarm_publish"


class AlarmPayload(ContractModel, Generic[ContentT]):
    """共通の警告情報と、機器固有の内容。"""

    detected_at: datetime = Field(
        description="このtrace_idで最初に異常を検知した時刻",
    )
    notification_attempt: int = Field(
        ge=0,
        description="初回0。同じ警告をAgentが再発信するたびに1増加",
    )
    content: ContentT


class AlarmPublish(ContractModel, Generic[ContentT]):
    """AgentからCentralへ送る警告。"""

    header: AlarmPublishHeader
    payload: AlarmPayload[ContentT]


class AlarmStoredHeader(TrackableHeader):
    type: Literal["alarm_stored"] = "alarm_stored"


class AlarmStoredPayload(ContractModel):
    stored_message_id: str = Field(
        min_length=1,
        description="保存確認の対象となる警告メッセージのID",
    )


class AlarmStored(ContractModel):
    """Centralで警告のDB保存が確定した通知。"""

    header: AlarmStoredHeader
    payload: AlarmStoredPayload


class AlarmAcknowledgedHeader(TrackableHeader):
    type: Literal["alarm_acknowledged"] = "alarm_acknowledged"


class AlarmAcknowledgedPayload(ContractModel):
    acknowledged_at: datetime = Field(
        description="Centralに記録されたユーザー確認の時刻",
    )


class AlarmAcknowledged(ContractModel):
    """Centralでユーザー確認の記録が確定した通知。"""

    header: AlarmAcknowledgedHeader
    payload: AlarmAcknowledgedPayload