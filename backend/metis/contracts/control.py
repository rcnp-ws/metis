# backend/src/metis/contracts/control.py

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from metis.contracts.base import ContractModel
from metis.contracts.header import TrackableHeader


PayloadT = TypeVar("PayloadT", bound=BaseModel)


class OperationRequestHeader(TrackableHeader):
    """CentralからAgentへ送る操作要求のヘッダー。"""

    type: Literal["operation_request"] = "operation_request"

    device_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)

    user_id: str = Field(
        min_length=1,
        description="Centralが認証結果から確定したユーザー",
    )
    ui_id: str = Field(
        min_length=1,
        description="要求元のブラウザー画面の識別子",
    )
    workflow_id: str | None = Field(
        default=None,
        min_length=1,
        description="複数Agentの処理を束ねる識別子",
    )


class OperationRequest(ContractModel, Generic[PayloadT]):
    """機器固有のペイロード型を指定して使用する操作要求。"""

    header: OperationRequestHeader
    payload: PayloadT


class OperationAcceptedHeader(TrackableHeader):
    type: Literal["operation_accepted"] = "operation_accepted"


class EmptyPayload(ContractModel):
    """項目を持たないペイロード。"""

    pass


class OperationAccepted(ContractModel):
    """Agentの永続受付が完了した通知。実行成功とは区別する。"""

    header: OperationAcceptedHeader
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


class OperationRejectedHeader(TrackableHeader):
    type: Literal["operation_rejected"] = "operation_rejected"


class RejectionReason(ContractModel):
    """受付前の拒否理由。"""

    code: str = Field(min_length=1)
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class OperationRejected(ContractModel):
    """Agentが要求を受け付けなかった通知。"""

    header: OperationRejectedHeader
    payload: RejectionReason
