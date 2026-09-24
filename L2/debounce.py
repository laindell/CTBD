import threading
from functools import wraps
from typing import Callable, Any


def debounce(
    fn: Callable,
    delay_ms: int,
    leading: bool = False,
    trailing: bool = True
) -> Callable:
    """
    Відкладає виконання fn до моменту,
    коли протягом delay_ms не буде нових викликів.

    leading=True  - виконати перший виклик одразу.
    trailing=True - виконати останній виклик після паузи.
    """

    timer = None
    last_args = None
    last_kwargs = None
    lock = threading.Lock()

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        nonlocal timer, last_args, last_kwargs

        with lock:
            last_args = args
            last_kwargs = kwargs

            # Якщо таймера немає — це перший виклик серії
            first_call = timer is None

            # Скасовуємо попередній таймер
            if timer is not None:
                timer.cancel()

            # Leading — виконуємо перший виклик одразу
            if first_call and leading:
                fn(*args, **kwargs)

                # Не потрібно повторно викликати цю функцію
                # через trailing, якщо це був єдиний виклик
                last_args = None
                last_kwargs = None

            def call_it():
                nonlocal timer, last_args, last_kwargs

                with lock:
                    # Trailing — виконуємо останній виклик
                    if trailing and last_args is not None:
                        fn(*last_args, **last_kwargs)

                    # Очищаємо стан
                    timer = None
                    last_args = None
                    last_kwargs = None

            # Timer працює в секундах
            timer = threading.Timer(
                delay_ms / 1000,
                call_it
            )
            timer.start()

    def dispose():
        """Скасовує запланований виклик."""
        nonlocal timer, last_args, last_kwargs

        with lock:
            if timer is not None:
                timer.cancel()
                timer = None

            last_args = None
            last_kwargs = None

    wrapper.dispose = dispose

    return wrapper