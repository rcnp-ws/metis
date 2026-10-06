import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from websockets.asyncio.client import connect

from metis.contracts.control import (
    OperationAccepted,
    OperationAcceptedHeader,
    OperationRejected,
    OperationRejectedHeader,
)
from metis.contracts.registration import (
    AgentRegister,
    AgentRegisterHeader,
    AgentRegisterPayload,
    AgentRegistered,
)

from metis.agent.generic import GenericAgent

logger = logging.getLogger(__name__)


def response_header(
    header_model: type[BaseModel],
    request_header: dict[str, Any],
    message_type: str,
) -> BaseModel:
    """要求の追跡情報を引き継ぎ、応答用ヘッダを生成する。"""
    values = {
        **request_header,
        "type": message_type,
        "sent_at": datetime.now(timezone.utc),
        "message_id": str(uuid4()),
    }

    # 応答ヘッダで定義されている項目だけを引き継ぐ。
    return header_model.model_validate(
        {
            name: values[name]
            for name in header_model.model_fields
            if name in values
        }
    )


async def receive_operation(
    agent: GenericAgent,
    message: dict[str, Any],
) -> BaseModel:
    """操作要求を検証し、永続受付後に応答モデルを返す。"""
    header = message["header"]

    # 拒否応答にも必要な追跡情報を先に検証する。
    rejected_header = response_header(
        OperationRejectedHeader,
        header,
        "operation_rejected",
    )

    def reject(code: str, reason: str) -> OperationRejected:
        return OperationRejected(
            header=rejected_header,
            payload={
                "code": code,
                "message": reason,
                "details": None,
            },
        )

    if header.get("device_id") != agent.agent_id:
        return reject(
            "device_mismatch",
            "このAgentの対象機器ではありません",
        )

    operation = header.get("operation")

    if not isinstance(operation, str):
        return reject(
            "invalid_operation",
            "操作名が指定されていません",
        )

    try:
        request_model = agent.operation_request_model(operation)
    except KeyError:
        return reject(
            "unknown_operation",
            f"未登録の操作です: {operation}",
        )

    try:
        operation_request = request_model.model_validate(message)
    except ValidationError:
        return reject(
            "invalid_request",
            "操作要求の形式またはペイロードが不正です",
        )

    # 受付前に応答モデルも組み立てる。
    accepted = OperationAccepted(
        header=response_header(
            OperationAcceptedHeader,
            header,
            "operation_accepted",
        ),
        payload={},
    )

    try:
        await agent.accept_operation(operation_request)

    except ValidationError:
        return reject(
            "invalid_request",
            "操作の入力検証に失敗しました",
        )

    except RuntimeError:
        return reject(
            "agent_unavailable",
            "Agentが操作を受け付けられる状態ではありません",
        )

    # SQLAlchemyErrorはここでは拒否に変換しない。
    # コミット結果が不明な可能性があるため接続側へ伝える。
    return accepted


async def connect_to_central(
    agent: GenericAgent,
    url: str,
    retry_interval: float = 3.0,
) -> None:
    """Centralへ登録し、操作要求を受信する。"""
    while True:
        try:
            async with connect(url) as websocket:
                registration = AgentRegister(
                    header=AgentRegisterHeader(
                        sent_at=datetime.now(timezone.utc),
                    ),
                    payload=AgentRegisterPayload.model_validate(
                        agent.describe(),
                    ),
                )

                await websocket.send(
                    registration.model_dump_json(),
                )

                raw = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=10.0,
                )
                registered = AgentRegistered.model_validate_json(raw)

                if registered.payload.agent_id != agent.agent_id:
                    raise ValueError(
                        "Registration response has a different agent_id"
                    )

                logger.info(
                    "Registered with Central: %s",
                    agent.agent_id,
                )

                async for raw in websocket:
                    message = json.loads(raw)

                    if not isinstance(message, dict):
                        raise ValueError("Message must be an object")

                    header = message.get("header")

                    if not isinstance(header, dict):
                        raise ValueError("Message header is required")

                    if header.get("type") != "operation_request":
                        raise ValueError(
                            f"Unsupported message type: "
                            f"{header.get('type')}"
                        )

                    response = await receive_operation(
                        agent,
                        message,
                    )

                    await websocket.send(
                        response.model_dump_json(),
                    )

        except asyncio.CancelledError:
            raise

        except SQLAlchemyError:
            logger.exception(
                "Operation acceptance unconfirmed; "
                "closing Central connection"
            )

        except Exception:
            logger.exception(
                "Central connection failed: %s",
                agent.agent_id,
            )

        await asyncio.sleep(retry_interval)