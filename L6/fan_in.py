import asyncio
from collections.abc import AsyncIterable, AsyncIterator
from typing import TypeVar

T = TypeVar("T")


async def fan_in(
    inputs: list[AsyncIterable[T]],
    errors: asyncio.Queue[Exception] | None = None,
) -> AsyncIterator[T]:
    """Merge async streams; errors from one input do not stop others."""
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    async def consume(stream: AsyncIterable[T]) -> None:
        try:
            async for item in stream:
                await queue.put(("item", item))
        except Exception as exc:
            if errors is not None:
                errors.put_nowait(exc)
        finally:
            await queue.put(("done", None))

    tasks = [asyncio.create_task(consume(stream)) for stream in inputs]
    completed = 0

    try:
        while completed < len(tasks):
            event, value = await queue.get()
            if event == "item":
                yield value  # type: ignore[misc]
            elif event == "done":
                completed += 1
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
