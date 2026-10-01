# backend/src/metis/central/api/agents.py

import asyncio

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from metis.central.connections.registry import AgentAlreadyConnectedError, AgentRegistry
from metis.contracts.registration import (
    AgentDescription,
    RegisterAgentAccepted,
    RegisterAgentRequest,
)
from pydantic import ValidationError

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentDescription])
async def list_agents(request: Request) -> list[AgentDescription]:
    """接続中の agent 一覧を取得する。"""
    registry: AgentRegistry = request.app.state.agent_registry
    return await registry.list_agents()


@router.websocket("/connect")
async def connect_agent(websocket: WebSocket) -> None:
    """agent の登録を受け付け、切断まで接続を保持する。"""
    registry: AgentRegistry = websocket.app.state.agent_registry

    await websocket.accept()

    registered_agent_id: str | None = None

    try:
        # 接続後、最初のメッセージとして登録情報を受け取る。
        try:
            raw = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=10.0,
            )
        except TimeoutError:
            await websocket.close(
                code=1008,
                reason="Registration timeout",
            )
            return

        try:
            registration = RegisterAgentRequest.model_validate_json(raw)
        except ValidationError:
            await websocket.close(
                code=1008,
                reason="Invalid registration",
            )
            return

        try:
            connection = await registry.register(
                description=registration.agent,
                websocket=websocket,
            )
        except AgentAlreadyConnectedError:
            await websocket.close(
                code=1008,
                reason="Agent ID already connected",
            )
            return

        registered_agent_id = registration.agent.agent_id

        accepted = RegisterAgentAccepted(
            agent_id=registered_agent_id,
        )

        async with connection.send_lock:
            await websocket.send_text(accepted.model_dump_json())

        # 現段階では登録後のメッセージ処理は未実装。
        # disconnect を受信するまで接続を保持する。
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            await websocket.close(
                code=1008,
                reason="Post-registration messages not implemented",
            )
            break

    except WebSocketDisconnect:
        pass

    finally:
        if registered_agent_id is not None:
            await registry.unregister(
                agent_id=registered_agent_id,
                websocket=websocket,
            )
