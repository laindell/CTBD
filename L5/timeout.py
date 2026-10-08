import concurrent.futures
from typing import Callable, Any

class TimeoutException(Exception):
    pass

def with_timeout(fn: Callable, timeout_ms: int, *args, **kwargs) -> Any:
    """
    Виконує функцію fn і відхиляє її з помилкою після timeout_ms.
    """
    timeout_sec = timeout_ms / 1000.0
    
    # Створюємо пул потоків без блоку with, щоб уникнути очікування при закритті
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args, **kwargs)
    
    try:
        return future.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        # Скасовуємо завдання, якщо воно ще не почало виконуватися
        future.cancel()
        raise TimeoutException(f"Operation timed out after {timeout_ms}ms")
    finally:
        # wait=False дозволяє основному потоку не чекати завершення завислої функції
        # cancel_futures=True скасовує всі завдання в черзі (працює в Python 3.9+)
        executor.shutdown(wait=False, cancel_futures=True)