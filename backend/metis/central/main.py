import asyncio
import logging
from datetime import datetime, timezone
from json import JSONDecodeError

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError

from metis.contracts.registration import (
    AgentRegister,
    AgentRegisterPayload,
    AgentRegistered,
    AgentRegisteredHeader,
    AgentRegisteredPayload,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Metis Central")

# この最小構成は単一プロセスで利用する。
connections: dict[str, WebSocket] = {}
registrations: dict[str, AgentRegisterPayload] = {}


@app.get("/agents")
async def list_agents() -> list[AgentRegisterPayload]:
    return list(registrations.values())


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> AgentRegisterPayload:
    registration = registrations.get(agent_id)

    if registration is None:
        raise HTTPException(
            status_code=404,
            detail="Agent is not connected",
        )

    return registration


@app.websocket("/ws/agents")
async def agent_connection(websocket: WebSocket) -> None:
    await websocket.accept()

    agent_id: str | None = None

    try:
        # 接続後、最初のメッセージは登録要求とする。
        raw = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10.0,
        )
        registration = AgentRegister.model_validate(raw)

        candidate_id = registration.payload.agent_id

        # 接続中の同じIDを上書きしない。
        if candidate_id in connections:
            await websocket.close(
                code=1008,
                reason="Agent ID is already connected",
            )
            return

        # この間にawaitを置かず、登録を一括して反映する。
        connections[candidate_id] = websocket
        registrations[candidate_id] = registration.payload
        agent_id = candidate_id

        response = AgentRegistered(
            header=AgentRegisteredHeader(
                sent_at=datetime.now(timezone.utc),
            ),
            payload=AgentRegisteredPayload(
                agent_id=agent_id,
            ),
        )

        await websocket.send_json(
            response.model_dump(mode="json"),
        )

        logger.info("Agent registered: %s", agent_id)

        # 次の段階で、監視・操作応答・警告の振り分けを追加する。
        # 現段階では、登録後のデータメッセージは未対応。
        while True:
            event = await websocket.receive()

            if event["type"] == "websocket.disconnect":
                break

            await websocket.close(
                code=1003,
                reason="Message handling is not implemented yet",
            )
            break

    except (ValidationError, JSONDecodeError):
        await websocket.close(
            code=1008,
            reason="Invalid registration message",
        )

    except asyncio.TimeoutError:
        await websocket.close(
            code=1008,
            reason="Registration timed out",
        )

    except WebSocketDisconnect:
        pass

    finally:
        # この接続自身が登録した情報だけを除去する。
        if (
            agent_id is not None
            and connections.get(agent_id) is websocket
        ):
            connections.pop(agent_id, None)
            registrations.pop(agent_id, None)
            logger.info("Agent disconnected: %s", agent_id)