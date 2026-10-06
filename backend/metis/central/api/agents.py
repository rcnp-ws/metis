# backend/src/metis/agent/generic.py

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from metis.contracts.control import OperationRequest


@dataclass
class Operation:
    """操作の定義。"""
    request_model: type[BaseModel]
    handler: Callable[[Any], Awaitable[Any]]


@dataclass
class Monitor:
    """モニターの定義。"""
    value_model: type[BaseModel]
    reader: Callable[[], Awaitable[BaseModel]]


class GenericAgent:
    
    def __init__(
        self,
        *,
        agent_id: str,
        device_type: str,
        on_start: Callable[[], Awaitable[None]],
        on_stop: Callable[[], Awaitable[None]],
    ) -> None:
        self.agent_id = agent_id
        self.device_type = device_type

        self._on_start = on_start
        self._on_stop = on_stop
        self._started = False

        self._operations: dict[str, Operation] = {}
        self._monitors: dict[str, Monitor] = {}

    def register_operation(
        self,
        *,
        name: str,
        request_model: type[BaseModel],
        handler: Callable[[Any], Awaitable[Any]],
    ) -> None:
    
        if not name or name in self._operations:
            raise ValueError(f"Invalid or duplicate operation: {name}")

        self._operations[name] = Operation(request_model, handler)

    def register_monitor(
        self,
        *,
        name: str,
        value_model: type[BaseModel],
        reader: Callable[[], Awaitable[BaseModel]],
    ) -> None:
        if not name or name in self._monitors:
            raise ValueError(f"Invalid or duplicate monitor: {name}")

        self._monitors[name] = Monitor(value_model, reader)

    def validate_operation(
        self,
        name: str,
        payload: dict[str, Any],
    ) -> BaseModel:
        """操作名に対応するモデルで入力を検証する。"""
        operation = self._operations[name]
        return operation.request_model.model_validate(payload)

    async def run_operation(
        self,
        name: str,
        request: BaseModel,
    ) -> None:
        """永続受付後に、検証済みの引数で操作を実行する。"""
        operation = self._operations[name]

        if not isinstance(request, operation.request_model):
            raise TypeError(f"Unexpected request model for: {name}")

        await operation.handler(request)

    async def read_monitor(self, name: str) -> BaseModel:
        monitor = self._monitors[name]
        value = await monitor.reader()
        return monitor.value_model.model_validate(value.model_dump())

    def operation_request_model(self, name: str) -> type[BaseModel]:
        operation = self._operations[name]
        return OperationRequest[operation.request_model]

    def describe(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "device_type": self.device_type,
            "operations": {
                name: {
                    "request_schema": operation.request_model.model_json_schema(),
                }
                for name, operation in self._operations.items()
            },
            "monitors": {
                name: {
                    "state_schema": monitor.value_model.model_json_schema(
                        mode="serialization",
                    ),
                }
                for name, monitor in self._monitors.items()
            },
        }

    async def start(self) -> None:
        if not self._started:
            await self._on_start()
            self._started = True

    async def stop(self) -> None:
        if self._started:
            await self._on_stop()
            self._started = False