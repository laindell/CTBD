import asyncio
from typing import Callable, Generic, TypeVar

Task = TypeVar("Task")
Result = TypeVar("Result")
_END = object()


class FanOut(Generic[Task, Result]):
    """Розподіляє задачі між N воркерами та збирає результати."""

    def __init__(self, process: Callable[[Task], Result], workers: int):
        if workers < 1:
            raise ValueError("workers має бути не менше 1")

        self.process = process
        self.queue: asyncio.Queue = asyncio.Queue()
        self._results: asyncio.Queue = asyncio.Queue()
        self._workers = [
            asyncio.create_task(self._worker())
            for _ in range(workers)
        ]
        self._closed = False
        self._results_started = False

    async def submit(self, task: Task) -> None:
        if self._closed:
            raise RuntimeError("FanOut вже закрито")
        await self.queue.put(task)

    async def _worker(self) -> None:
        while True:
            task = await self.queue.get()
            try:
                if task is None:
                    return
                result = await asyncio.to_thread(self.process, task)
                await self._results.put(result)
            finally:
                self.queue.task_done()

    async def results(self):
        """Видає результати; завершується після close()."""
        if self._results_started:
            raise RuntimeError("results() можна читати лише один раз")
        self._results_started = True
        while True:
            result = await self._results.get()
            self._results.task_done()
            if result is _END:
                break
            yield result

    async def close(self) -> None:
        """Graceful shutdown: дочікується задач і зупиняє воркерів."""
        if self._closed:
            return
        self._closed = True
        await self.queue.join()
        for _ in self._workers:
            await self.queue.put(None)
        await asyncio.gather(*self._workers)
        await self._results.put(_END)
