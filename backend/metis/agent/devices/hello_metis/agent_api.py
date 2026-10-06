import logging
import asyncio

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError

from metis.agent.generic import GenericAgent
from metis.contracts.control import OperationRequest

from metis.agent.devices.hello_metis.agent import create_agent
from metis.agent.devices.hello_metis.models import GreetingValue, RegisterNameRequest

from metis.agent.connection import connect_to_central

logger = logging.getLogger(__name__)

RegisterNameOperationRequest = OperationRequest[
    RegisterNameRequest
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    agent, store = create_agent()
    connection_task: asyncio.Task[None] | None = None

    try:
        await agent.start()
        app.state.agent = agent

        connection_task = asyncio.create_task(
            connect_to_central(
                agent,
                "ws://127.0.0.1:8000/ws/agents",
            ),
        )

        yield

    finally:
        try:
            if connection_task is not None:
                connection_task.cancel()

                try:
                    await connection_task
                except asyncio.CancelledError:
                    pass
        finally:
            try:
                await agent.stop()
            finally:
                store.close()


app = FastAPI(
    title="hello_metis Agent API",
    lifespan=lifespan,
)


def get_agent(request: Request) -> GenericAgent:
    return request.app.state.agent


@app.get("/description")
async def description(request: Request) -> dict:
    return get_agent(request).describe()


@app.get(
    "/monitors/greeting",
    response_model=GreetingValue,
)
async def greeting(request: Request) -> GreetingValue:
    value = await get_agent(request).read_monitor("greeting")
    return GreetingValue.model_validate(value.model_dump())


@app.post(
    "/operations/register_name",
    status_code=status.HTTP_202_ACCEPTED,
)
async def register_name(
    payload: RegisterNameRequest,
    request: Request,
) -> dict[str, str]:
    agent = get_agent(request)

    # 単独動作確認用として、このAPIがヘッダを生成する。
    operation_request = (
        RegisterNameOperationRequest.model_validate(
            {
                "header": {
                    "type": "operation_request",
                    "sent_at": datetime.now(timezone.utc),
                    "message_id": str(uuid4()),
                    "trace_id": str(uuid4()),
                    "device_id": agent.agent_id,
                    "operation": "register_name",
                    "user_id": "local-test",
                    "ui_id": "local-test",
                },
                "payload": payload.model_dump(),
            }
        )
    )

    try:
        await agent.accept_operation(operation_request)

    except SQLAlchemyError:
        logger.exception("Operation persistence failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "acceptance_unconfirmed",
                "message": "操作の受付を確認できませんでした",
                "trace_id": operation_request.header.trace_id,
            },
        ) from None

    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agentが操作を受け付けられる状態ではありません",
        ) from None

    return {
        "status": "accepted",
        "trace_id": operation_request.header.trace_id,
    }