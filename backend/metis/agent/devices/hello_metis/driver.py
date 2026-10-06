import asyncio
import random

from metis.agent.devices.hello_metis.models import GreetingValue, RegisterNameRequest


class HelloMetisDriver:
    def __init__(self, interval: float = 1.0) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")

        self._interval = interval
        self._counts: dict[str, int] = {}
        self._last_name: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._greet())

    async def stop(self) -> None:
        if self._task is None:
            return

        task = self._task
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
    ) -> None:
        self._counts.setdefault(request.name, 0)

    async def read_greeting(self) -> GreetingValue:
        return GreetingValue(
            name=self._last_name,
            counts=self._counts.copy(),
        )

    async def _greet(self) -> None:
        while True:
            await asyncio.sleep(self._interval)

            if not self._counts:
                continue

            name = random.choice(list(self._counts))
            self._counts[name] += 1
            self._last_name = name