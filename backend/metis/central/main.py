# backend/src/metis/central/main.py

import asyncio
import logging
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any
from uuid import uuid4

from fastapi import (
    Body,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError

from metis.contracts.control import (
    OperationAccepted,
    OperationRejected,
    OperationRequestHeader,
)
from metis.contracts.registration import (
    AgentRegister,
    AgentRegisterPayload,
    AgentRegistered,
    AgentRegisteredHeader,
    AgentRegisteredPayload,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Metis Central")

OperationResponse = OperationAccepted | OperationRejected


class AgentConnection:
    """一つの接続と、その接続で応答待ちの操作を保持する。"""

    def __init__(
        self,
        websocket: WebSocket,
        registration: AgentRegisterPayload,
    ) -> None:
        self.websocket = websocket
        self.registration = registration

        self.send_lock = asyncio.Lock()
        self.pending: dict[
            str,
            asyncio.Future[OperationResponse],
        ] = {}

    def disconnected(self) -> None:
        for future in self.pending.values():
            if not future.done():
                future.set_exception(
                    ConnectionError("Agent disconnected"),
                )


# 単一プロセスで利用する。
connections: dict[str, AgentConnection] = {}


@app.get("/agents")
async def list_agents() -> list[AgentRegisterPayload]:
    return [
        connection.registration
        for connection in connections.values()
    ]


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> AgentRegisterPayload:
    connection = connections.get(agent_id)

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="Agent is not connected",
        )

    return connection.registration


@app.websocket("/ws/agents")
async def agent_connection(websocket: WebSocket) -> None:
    await websocket.accept()

    agent_id: str | None = None
    connection: AgentConnection | None = None

    try:
        raw = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10.0,
        )
        registration = AgentRegister.model_validate(raw)
        candidate_id = registration.payload.agent_id

        if candidate_id in connections:
            await websocket.close(
                code=1008,
                reason="Agent ID is already connected",
            )
            return

        connection = AgentConnection(
            websocket,
            registration.payload,
        )

        registered = AgentRegistered(
            header=AgentRegisteredHeader(
                sent_at=datetime.now(timezone.utc),
            ),
            payload=AgentRegisteredPayload(
                agent_id=candidate_id,
            ),
        )

        # 登録応答を先に送る。
        # 操作要求が登録応答を追い越すことを防ぐ。
        await websocket.send_json(
            registered.model_dump(mode="json"),
        )

        # 応答送信中に同じIDの接続が登録されていないか再確認。
        if candidate_id in connections:
            await websocket.close(
                code=1008,
                reason="Agent ID is already connected",
            )
            return

        agent_id = candidate_id
        connections[agent_id] = connection

        logger.info("Agent registered: %s", agent_id)

        while True:
            message = await websocket.receive_json()

            if not isinstance(message, dict):
                raise ValueError("Message must be an object")

            header = message.get("header")

            if not isinstance(header, dict):
                raise ValueError("Message header is required")

            message_type = header.get("type")

            if message_type == "operation_accepted":
                response = OperationAccepted.model_validate(message)

            elif message_type == "operation_rejected":
                response = OperationRejected.model_validate(message)

            else:
                await websocket.close(
                    code=1003,
                    reason="Unsupported message type",
                )
                return

            future = connection.pending.get(
                response.header.trace_id,
            )

            if future is not None and not future.done():
                future.set_result(response)
            else:
                logger.warning(
                    "Late or unknown operation response: %s",
                    response.header.trace_id,
                )

    except (ValidationError, JSONDecodeError, ValueError):
        await websocket.close(
            code=1008,
            reason="Invalid message",
        )

    except asyncio.TimeoutError:
        await websocket.close(
            code=1008,
            reason="Registration timed out",
        )

    except WebSocketDisconnect:
        pass

    finally:
        if connection is not None:
            connection.disconnected()

        if (
            agent_id is not None
            and connections.get(agent_id) is connection
        ):
            connections.pop(agent_id, None)
            logger.info("Agent disconnected: %s", agent_id)


@app.post(
    "/agents/{agent_id}/operations/{operation}",
    status_code=202,
)
async def request_operation(
    agent_id: str,
    operation: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    connection = connections.get(agent_id)

    if connection is None:
        raise HTTPException(
            status_code=503,
            detail="Agent is not connected",
        )

    if operation not in connection.registration.operations:
        raise HTTPException(
            status_code=404,
            detail="Unknown operation",
        )

    trace_id = str(uuid4())

    header = OperationRequestHeader(
        type="operation_request",
        sent_at=datetime.now(timezone.utc),
        message_id=str(uuid4()),
        trace_id=trace_id,
        device_id=agent_id,
        operation=operation,
        user_id="local-test",
        ui_id="local-test",
    )

    # 機器固有のペイロード検証はAgentが行う。
    message = {
        "header": header.model_dump(mode="json"),
        "payload": payload,
    }

    future: asyncio.Future[OperationResponse] = (
        asyncio.get_running_loop().create_future()
    )

    # 送信前に登録し、即時の応答も受け取れるようにする。
    connection.pending[trace_id] = future

    try:
        # タイムアウトは送信待ちも含める。
        async with asyncio.timeout(10.0):
            async with connection.send_lock:
                await connection.websocket.send_json(message)

            response = await future

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "acceptance_unconfirmed",
                "message": "操作の受付を確認できませんでした",
                "trace_id": trace_id,
            },
        ) from None

    except (ConnectionError, OSError, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "acceptance_unconfirmed",
                "message": "Agentとの通信が中断しました",
                "trace_id": trace_id,
            },
        ) from None

    finally:
        connection.pending.pop(trace_id, None)

        if not future.done():
            future.cancel()
        elif not future.cancelled():
            # 送信失敗と切断が重なった場合も例外を回収する。
            future.exception()

    if isinstance(response, OperationRejected):
        raise HTTPException(
            status_code=409,
            detail=response.model_dump(mode="json"),
        )

    return response.model_dump(mode="json")