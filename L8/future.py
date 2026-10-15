import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
_executor = ThreadPoolExecutor()


class Future(Generic[T]):
    def __init__(self):
        self._future = asyncio.get_running_loop().create_future()

    @property
    def done(self) -> bool:
        return self._future.done()

    def _resolve(self, value: T) -> None:
        if not self._future.done():
            self._future.set_result(value)

    def _reject(self, error: BaseException) -> None:
        if not self._future.done():
            self._future.set_exception(error)

    def then(self, callback: Callable[[T], object]) -> "Future":
        chained = Future()

        def complete(source):
            try:
                value = source.result()
                result = callback(value)

                if isinstance(result, Future):
                    async def transfer():
                        try:
                            chained._resolve(await result.get())
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            chained._reject(exc)

                    asyncio.create_task(transfer())
                else:
                    chained._resolve(result)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                chained._reject(exc)

        self._future.add_done_callback(complete)
        return chained

    def catch(self, callback: Callable[[BaseException], object]) -> "Future":
        chained = Future()

        def complete(source):
            try:
                chained._resolve(source.result())

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                try:
                    chained._resolve(callback(exc))
                except asyncio.CancelledError:
                    raise
                except Exception as callback_error:
                    chained._reject(callback_error)

        self._future.add_done_callback(complete)
        return chained

    onError = catch

    async def get(self, timeout: float | None = None) -> T:
        return await asyncio.wait_for(
            asyncio.shield(self._future),
            timeout=timeout
        )


def submit(fn: Callable[..., T], *args, **kwargs) -> Future[T]:
    future = Future()

    async def run():
        loop = asyncio.get_running_loop()

        try:
            result = await loop.run_in_executor(
                _executor,
                lambda: fn(*args, **kwargs)
            )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            future._reject(exc)

        else:
            future._resolve(result)

    asyncio.create_task(run())
    return future


async def all(futures: list[Future]) -> list:
    return list(
        await asyncio.gather(
            *(future.get() for future in futures)
        )
    )


async def race(futures: list[Future]):
    if not futures:
        raise ValueError("race потребує хоча б одного Future")

    wrapped = [
        asyncio.create_task(future.get())
        for future in futures
    ]

    done, pending = await asyncio.wait(
        wrapped,
        return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()

    await asyncio.gather(
        *pending,
        return_exceptions=True
    )

    return await next(iter(done))