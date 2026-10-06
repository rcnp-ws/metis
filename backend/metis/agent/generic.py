"""Agent共通の操作・監視と、永続受付後の順次実行。

accept_operation(request):
    検証、DBコミット、FIFOキューへの予約。
    正常終了後、通信側がOperationAcceptedを生成して送信する。

validate_operation / run_operation:
    従来の低レベルAPI。
    直接run_operationを呼んでも永続化は行わないため、
    通信からの要求はaccept_operationを使う。

on_operation_error(trace_id, reason):
    警告生成・保存・配送への接続点。
    コールバックで警告を永続化できない場合も配送を試みること。

start():
    未完了操作をunknownに更新し、Driverと実行ワーカーを起動する。

stop():
    新規受付を止め、キューを処理してDriverを停止する。
    Driverが終了しなければstopも待ち続ける。
    強制終了後は自動再実行しない。

Storeのcloseは生成した側がstop完了後に呼ぶ。
同じDBを複数のAgentプロセスで共有しない。
SUCCEEDEDはhandlerの正常終了を表し、
物理状態の到達判定はhandlerの責務。
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from metis.agent.storage import AgentRecordStore, OperationStatus
from metis.contracts.control import OperationRequest

logger = logging.getLogger(__name__)


@dataclass
class Operation:
    request_model: type[BaseModel]
    handler: Callable[[Any], Awaitable[Any]]


@dataclass
class Monitor:
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
        store: AgentRecordStore,
        on_operation_error: Callable[
            [str, dict[str, Any]],
            Awaitable[None],
        ],
    ) -> None:
        self.agent_id = agent_id
        self.device_type = device_type

        self._on_start = on_start
        self._on_stop = on_stop
        self._started = False

        self._store = store
        self._on_operation_error = on_operation_error

        self._accept_lock = asyncio.Lock()
        self._queue: asyncio.Queue[
            tuple[OperationRequest[Any], BaseModel] | None
        ] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

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
            raise ValueError(
                f"Invalid or duplicate operation: {name}"
            )

        self._operations[name] = Operation(
            request_model,
            handler,
        )

    def register_monitor(
        self,
        *,
        name: str,
        value_model: type[BaseModel],
        reader: Callable[[], Awaitable[BaseModel]],
    ) -> None:
        if not name or name in self._monitors:
            raise ValueError(
                f"Invalid or duplicate monitor: {name}"
            )

        self._monitors[name] = Monitor(
            value_model,
            reader,
        )

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
            raise TypeError(
                f"Unexpected request model for: {name}"
            )

        await operation.handler(request)

    async def accept_operation(
        self,
        request: OperationRequest[Any],
    ) -> None:
        """検証・コミット・実行予約を行う。

        正常終了後に通信側が受理応答を返す。
        検証エラーは拒否に変換できる。
        DBエラー時は受付未確認とする。

        キャンセルや受理応答の配送失敗で、
        保存済みの操作は取り消さない。
        """
        async with self._accept_lock:
            if (
                not self._started
                or self._worker is None
                or self._worker.done()
            ):
                raise RuntimeError("Agent is not started")

            request = request.model_copy(deep=True)

            payload = self.validate_operation(
                request.header.operation,
                request.payload.model_dump(),
            )

            request = request.model_copy(
                update={"payload": payload},
            )

            saving = asyncio.create_task(
                asyncio.to_thread(
                    self._store.save_operation,
                    request,
                )
            )

            cancelled = False

            # スレッドのコミット結果を確定してから実行を予約する。
            while True:
                try:
                    await asyncio.shield(saving)
                    break
                except asyncio.CancelledError:
                    cancelled = True

            self._queue.put_nowait((request, payload))

            if cancelled:
                raise asyncio.CancelledError

    async def _report_operation_error(
        self,
        trace_id: str,
        reason: dict[str, Any],
    ) -> None:
        logger.error(
            "Operation %s: %s",
            trace_id,
            reason,
        )

        try:
            await self._on_operation_error(trace_id, reason)
        except Exception:
            logger.exception(
                "Operation error notification failed: %s",
                trace_id,
            )

    async def _update_operation(
        self,
        trace_id: str,
        status: OperationStatus,
        reason: dict[str, Any] | None = None,
    ) -> bool:
        try:
            await asyncio.to_thread(
                self._store.update_operation,
                trace_id,
                status,
                reason,
            )
            return True

        except Exception as exc:
            await self._report_operation_error(
                trace_id,
                {
                    "code": "operation_state_save_failed",
                    "message": str(exc),
                    "details": {
                        "intended_status": status.value,
                        "operation_reason": reason,
                    },
                },
            )
            return False

    async def _execute_operation(
        self,
        request: OperationRequest[Any],
        payload: BaseModel,
    ) -> None:
        trace_id = request.header.trace_id

        if not await self._update_operation(
            trace_id,
            OperationStatus.PROCESSING,
        ):
            # この実装案では、実行中を保存できなければ
            # 機器操作を開始しない。
            await self._update_operation(
                trace_id,
                OperationStatus.UNKNOWN,
                {
                    "code": "execution_not_started",
                    "message": (
                        "Could not persist processing state; "
                        "driver was not called"
                    ),
                },
            )
            return

        try:
            await self.run_operation(
                request.header.operation,
                payload,
            )

        except asyncio.CancelledError:
            reason = {
                "code": "execution_cancelled",
                "message": "Execution was interrupted",
            }

            await self._update_operation(
                trace_id,
                OperationStatus.UNKNOWN,
                reason,
            )
            await self._report_operation_error(
                trace_id,
                reason,
            )
            raise

        except Exception as exc:
            reason = {
                "code": "operation_execution_failed",
                "message": str(exc),
            }

            await self._update_operation(
                trace_id,
                OperationStatus.FAILED,
                reason,
            )
            await self._report_operation_error(
                trace_id,
                reason,
            )

        else:
            if not await self._update_operation(
                trace_id,
                OperationStatus.SUCCEEDED,
            ):
                await self._update_operation(
                    trace_id,
                    OperationStatus.UNKNOWN,
                    {
                        "code": "operation_result_save_failed",
                        "message": (
                            "Driver returned normally but "
                            "result persistence failed"
                        ),
                    },
                )

    async def _run_queue(self) -> None:
        while True:
            item = await self._queue.get()

            try:
                if item is None:
                    return

                await self._execute_operation(*item)

            finally:
                self._queue.task_done()

    async def read_monitor(self, name: str) -> BaseModel:
        monitor = self._monitors[name]
        value = await monitor.reader()

        return monitor.value_model.model_validate(
            value.model_dump(),
        )

    def operation_request_model(
        self,
        name: str,
    ) -> type[BaseModel]:
        operation = self._operations[name]
        return OperationRequest[operation.request_model]

    def describe(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "device_type": self.device_type,
            "operations": {
                name: {
                    "request_schema": (
                        operation.request_model.model_json_schema()
                    ),
                }
                for name, operation in self._operations.items()
            },
            "monitors": {
                name: {
                    "state_schema": (
                        monitor.value_model.model_json_schema(
                            mode="serialization",
                        )
                    ),
                }
                for name, monitor in self._monitors.items()
            },
        }

    async def start(self) -> None:
        async with self._accept_lock:
            if self._started:
                return

            await asyncio.to_thread(
                self._store.mark_interrupted_operations_unknown,
            )

            await self._on_start()

            self._worker = asyncio.create_task(
                self._run_queue(),
            )
            self._started = True

    async def stop(self) -> None:
        async with self._accept_lock:
            if not self._started:
                return

            self._started = False

            # 受付済みの処理を終えてからDriverを停止する。
            self._queue.put_nowait(None)

            assert self._worker is not None
            await self._worker
            self._worker = None

            await self._on_stop()