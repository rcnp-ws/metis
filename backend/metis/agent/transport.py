# backend/src/metis/agent/transport.py

import asyncio
import logging

from metis.contracts.registration import (
    AgentDescription,
    RegisterAgentAccepted,
    RegisterAgentRequest,
)
from pydantic import ValidationError
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from .generic import GenericAgent

logger = logging.getLogger(__name__)


class RegistrationProtocolError(Exception):
    """central の登録応答が期待する形式と異なる。"""


class AgentTransport:
    def __init__(
        self,
        *,
        agent: GenericAgent,
        central_url: str,
        reconnect_interval_seconds: float = 5.0,
    ) -> None:
        if reconnect_interval_seconds <= 0:
            raise ValueError("Reconnect interval must be positive")

        self._agent = agent
        self._central_url = central_url
        self._reconnect_interval = reconnect_interval_seconds

        self._task: asyncio.Task[None] | None = None
        self._registered = False

    @property
    def registered(self) -> bool:
        """登録応答を受け取り、接続を維持しているか。"""
        return self._registered

    async def start(self) -> None:
        """バックグラウンドで接続処理を開始する。"""
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """接続処理を停止し、WebSocket を閉じる。"""
        task = self._task
        if task is None:
            return

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            self._registered = False

    async def _run(self) -> None:
        while True:
            try:
                await self._connect_once()
            except (
                OSError,
                TimeoutError,
                ConnectionClosed,
                InvalidHandshake,
                ValidationError,
                RegistrationProtocolError,
            ) as exc:
                logger.warning(
                    "Central connection failed: %s",
                    exc,
                )
            finally:
                self._registered = False

            # 正常切断でも、接続エラーでも再接続する。
            await asyncio.sleep(self._reconnect_interval)

    async def _connect_once(self) -> None:
        description = AgentDescription.model_validate(self._agent.describe())
        registration = RegisterAgentRequest(agent=description)

        async with connect(
            self._central_url,
            open_timeout=10,
            close_timeout=5,
            ping_interval=20,
            ping_timeout=20,
        ) as websocket:
            await websocket.send(registration.model_dump_json())

            raw = await asyncio.wait_for(
                websocket.recv(),
                timeout=10,
            )
            accepted = RegisterAgentAccepted.model_validate_json(raw)

            if accepted.agent_id != self._agent.agent_id:
                raise RegistrationProtocolError(
                    "Registration response has a different agent ID"
                )

            self._registered = True
            logger.info(
                "Agent registered: %s",
                self._agent.agent_id,
            )

            # 次の段階で、ここに操作要求の受信処理を追加する。
            async for message in websocket:
                raise RegistrationProtocolError(
                    "Post-registration messages not implemented"
                )
