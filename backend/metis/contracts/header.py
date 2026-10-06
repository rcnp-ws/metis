# backend/src/metis/contracts/header.py

from datetime import datetime

from pydantic import Field

from metis.contracts.base import ContractModel


class MessageHeader(ContractModel):
    """メッセージ共通のヘッダー。"""

    type: str = Field(
        min_length=1,
        description="メッセージ種別",
    )
    sent_at: datetime = Field(
        description="メッセージの送信開始直前の時刻",
    )


class TrackableHeader(MessageHeader):
    """追跡に必要な識別子を持つヘッダー。"""

    message_id: str = Field(
        min_length=1,
        description="個々のメッセージを識別するID",
    )
    trace_id: str = Field(
        min_length=1,
        description="一制御または発報からユーザー確認までの流れを識別するID",
    )