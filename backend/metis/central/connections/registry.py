# backend/src/metis/central/connections/registry.py

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket
from metis.contracts.registration import AgentDescription


class AgentAlreadyConnectedError(LookupError):
    pass


class AgentNotConnectedError(LookupError):
    pass


@dataclass
class AgentConnection:
    """登録情報と、その agent への接続。"""

    description: AgentDescription
    websocket: WebSocket

    # 同じ接続への送信が重ならないようにする。
    send_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        repr=False,
    )


class AgentRegistry:
    def __init__(self) -> None:
        self._connections: dict[str, AgentConnection] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        description: AgentDescription,
        websocket: WebSocket,
    ) -> AgentConnection:
        """agent を登録する。同じ ID の接続があれば拒否する。"""
        async with self._lock:
            agent_id = description.agent_id

            if agent_id in self._connections:
                raise AgentAlreadyConnectedError(agent_id)

            connection = AgentConnection(
                description=description.model_copy(deep=True),
                websocket=websocket,
            )
            self._connections[agent_id] = connection

            return connection

    async def unregister(
        self,
        agent_id: str,
        websocket: WebSocket,
    ) -> bool:
        """指定された接続と一致する場合だけ登録を解除する。"""
        async with self._lock:
            connection = self._connections.get(agent_id)

            if connection is None:
                return False

            if connection.websocket is not websocket:
                return False

            del self._connections[agent_id]
            return True

    async def get_connection(
        self,
        agent_id: str,
    ) -> AgentConnection:
        """接続を取得する。"""
        async with self._lock:
            connection = self._connections.get(agent_id)

            if connection is None:
                raise AgentNotConnectedError(agent_id)

            return connection

    async def list_agents(self) -> list[AgentDescription]:
        """接続中の agent の登録情報を取得する。"""
        async with self._lock:
            return [
                connection.description.model_copy(deep=True)
                for connection in self._connections.values()
            ]
