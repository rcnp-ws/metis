# backend/src/metis/contracts/control.py

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ControlModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RejectionReason(ControlModel):
    """拒否・失敗の理由。"""

    code: str = Field(min_length=1)
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class OperationRequest(ControlModel):
    """central から agent に送る操作要求。"""

    type: Literal["operation_request"] = "operation_request"
    request_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class OperationAccepted(ControlModel):
    """agent が操作を受け付けた通知。実行完了ではない。"""

    type: Literal["operation_accepted"] = "operation_accepted"
    request_id: str = Field(min_length=1)


class OperationRejected(ControlModel):
    """操作を実行せず、受付を拒否した通知。"""

    type: Literal["operation_rejected"] = "operation_rejected"
    request_id: str = Field(min_length=1)
    reason: RejectionReason


class OperationSucceeded(ControlModel):
    """操作が正常に完了した通知。"""

    type: Literal["operation_succeeded"] = "operation_succeeded"
    request_id: str = Field(min_length=1)
    result: dict[str, Any]


class OperationFailed(ControlModel):
    """受け付けた操作の実行が失敗した通知。"""

    type: Literal["operation_failed"] = "operation_failed"
    request_id: str = Field(min_length=1)
    reason: RejectionReason
