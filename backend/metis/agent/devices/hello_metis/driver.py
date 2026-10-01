# backend/src/metis/devices/hello_metis/driver.py

import asyncio
import random
from datetime import datetime, timezone

from .models import (
    Greeting,
    HelloMetisConfig,
    HelloMetisState,
    PersonState,
    RegisterNameRequest,
    RegisterNameResult,
)


class HelloMetisDriver:
    def __init__(self, config: HelloMetisConfig) -> None:
        self._interval = config.greeting_interval_seconds
        self._counts: dict[str, int] = {}
        self._last_greeting: Greeting | None = None

        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """定期的な挨拶を開始する。繰り返し呼んでも多重起動しない。"""
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """定期的な挨拶を停止する。"""
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

    async def register_name(
        self,
        request: RegisterNameRequest,
    ) -> RegisterNameResult:
        """名前を登録する。登録済みなら累積回数を維持する。"""
        async with self._lock:
            created = request.name not in self._counts

            if created:
                self._counts[request.name] = 0

            return RegisterNameResult(
                name=request.name,
                created=created,
            )

    async def greet_once(self) -> Greeting | None:
        """ランダムな相手へ１回挨拶する。未登録なら何もしない。"""
        async with self._lock:
            if not self._counts:
                return None

            name = random.choice(list(self._counts))
            self._counts[name] += 1

            greeting = Greeting(
                name=name,
                count=self._counts[name],
                greeted_at=datetime.now(timezone.utc),
            )
            self._last_greeting = greeting

            # 内部状態を呼び出し側から変更されないようコピーする。
            return greeting.model_copy(deep=True)

    async def read_state(self) -> HelloMetisState:
        """現在の監視値を取得する。"""
        async with self._lock:
            return HelloMetisState(
                people=[
                    PersonState(name=name, count=count)
                    for name, count in self._counts.items()
                ],
                last_greeting=(
                    self._last_greeting.model_copy(deep=True)
                    if self._last_greeting is not None
                    else None
                ),
            )

    async def _run(self) -> None:
        """指定された間隔で挨拶する。"""
        while True:
            await asyncio.sleep(self._interval)
            await self.greet_once()
