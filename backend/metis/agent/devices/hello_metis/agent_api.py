# backend/src/metis/devices/hello_metis/agent_api.py

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from metis.agent.transport import AgentTransport

from .agent import create_agent
from .models import (
    HelloMetisConfig,
    HelloMetisState,
    RegisterNameRequest,
    RegisterNameResult,
)


def create_app(
    *,
    agent_id: str = "hello-metis-01",
    config: HelloMetisConfig | None = None,
    central_url: str = "ws://127.0.0.1:8000/agents/connect",
) -> FastAPI:
    agent = create_agent(
        agent_id=agent_id,
        config=config,
    )

    transport = AgentTransport(
        agent=agent,
        central_url=central_url,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await agent.start()
        try:
            await transport.start()
            try:
                yield
            finally:
                await transport.stop()
        finally:
            await agent.stop()

    app = FastAPI(
        title="hello_metis Agent API",
        lifespan=lifespan,
    )

    app.state.agent = agent
    app.state.transport = transport

    # ここから下は、既存のエンドポイント定義を維持する。

    @app.get("/description")
    async def describe() -> dict[str, Any]:
        """agent の機能情報とスキーマを取得する。"""
        return agent.describe()

    @app.post(
        "/operations/register_name",
        response_model=RegisterNameResult,
    )
    async def register_name(
        request: RegisterNameRequest,
    ) -> RegisterNameResult:
        """相手の名前を登録する。"""
        result = await agent.execute(
            "register_name",
            request.model_dump(),
        )
        return RegisterNameResult.model_validate(
            result.model_dump(),
        )

    @app.get(
        "/monitors/state",
        response_model=HelloMetisState,
    )
    async def read_state() -> HelloMetisState:
        """登録された相手と、最後の挨拶を取得する。"""
        state = await agent.read_monitor("state")
        return HelloMetisState.model_validate(
            state.model_dump(),
        )

    return app
