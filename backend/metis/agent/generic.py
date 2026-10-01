# backend/src/metis/agent/generic.py

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

LifecycleHook = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class Operation:
    request_model: type[BaseModel]
    result_model: type[BaseModel]
    handler: Callable[[Any], Awaitable[BaseModel]]


@dataclass(frozen=True)
class Monitor:
    state_model: type[BaseModel]
    reader: Callable[[], Awaitable[BaseModel]]


class UnknownOperationError(LookupError):
    pass


class UnknownMonitorError(LookupError):
    pass


class GenericAgent:
    def __init__(
        self,
        *,
        agent_id: str,
        device_type: str,
        on_start: LifecycleHook,
        on_stop: LifecycleHook,
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
        result_model: type[BaseModel],
        handler: Callable[[Any], Awaitable[BaseModel]],
    ) -> None:
        """操作と、その入力・結果のモデルを登録する。"""
        if name in self._operations:
            raise ValueError(f"Operation already registered: {name}")

        self._operations[name] = Operation(
            request_model=request_model,
            result_model=result_model,
            handler=handler,
        )

    def register_monitor(
        self,
        *,
        name: str,
        state_model: type[BaseModel],
        reader: Callable[[], Awaitable[BaseModel]],
    ) -> None:
        """監視値と、その取得関数を登録する。"""
        if name in self._monitors:
            raise ValueError(f"Monitor already registered: {name}")

        self._monitors[name] = Monitor(
            state_model=state_model,
            reader=reader,
        )

    async def start(self) -> None:
        """driver の処理を開始する。"""
        if self._started:
            return

        await self._on_start()
        self._started = True

    async def stop(self) -> None:
        """driver の処理を停止する。"""
        if not self._started:
            return

        await self._on_stop()
        self._started = False

    async def execute(
        self,
        name: str,
        payload: dict[str, Any],
    ) -> BaseModel:
        """入力を検証し、指定された操作を実行する。"""
        try:
            operation = self._operations[name]
        except KeyError:
            raise UnknownOperationError(name) from None

        request = operation.request_model.model_validate(payload)
        result = await operation.handler(request)

        return self._validate_output(operation.result_model, result)

    async def read_monitor(self, name: str) -> BaseModel:
        """指定された監視値を取得し、形式を検証する。"""
        try:
            monitor = self._monitors[name]
        except KeyError:
            raise UnknownMonitorError(name) from None

        state = await monitor.reader()

        return self._validate_output(monitor.state_model, state)

    def describe(self) -> dict[str, Any]:
        """agent の機能情報と JSON Schema を返す。"""
        return {
            "agent_id": self.agent_id,
            "device_type": self.device_type,
            "operations": {
                name: {
                    "request_schema": operation.request_model.model_json_schema(
                        mode="validation",
                    ),
                    "result_schema": operation.result_model.model_json_schema(
                        mode="serialization",
                    ),
                }
                for name, operation in self._operations.items()
            },
            "monitors": {
                name: {
                    "state_schema": monitor.state_model.model_json_schema(
                        mode="serialization",
                    ),
                }
                for name, monitor in self._monitors.items()
            },
        }

    @staticmethod
    def _validate_output(
        model: type[BaseModel],
        value: BaseModel,
    ) -> BaseModel:
        """driver の出力を、登録されたモデルで再検証する。"""
        return model.model_validate(value.model_dump())
