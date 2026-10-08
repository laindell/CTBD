import time
import threading
from collections import deque
from typing import Callable, Any

class Throttle:
    def __init__(self, max_calls: int, interval: float, mode: str = 'drop', leading: bool = True, trailing: bool = False):
        """
        :param max_calls: Максимальна кількість викликів у вікні.
        :param interval: Часове вікно в секундах.
        :param mode: 'drop' (відсікати надлишок) або 'queue' (чекати звільнення вікна).
        :param leading: Чи виконувати перший виклик одразу.
        :param trailing: Чи виконувати останній відкинутий виклик після завершення вікна (лише для 'drop').
        """
        self.max_calls = max_calls
        self.interval = interval
        self.mode = mode
        self.leading = leading
        self.trailing = trailing
        
        self.timestamps = deque()
        self.lock = threading.Lock()
        self.trailing_timer = None
        self.last_args = None
        self.last_kwargs = None
        self.fn = None

    def throttle(self, fn: Callable) -> Callable:
        self.fn = fn
        def wrapper(*args, **kwargs) -> Any:
            if self.mode == 'queue':
                return self._handle_queue(args, kwargs)
            else:
                return self._handle_drop(args, kwargs)
        return wrapper

    def _cleanup(self, now: float):
        # Видаляємо мітки часу, що вже вийшли за межі вікна
        while self.timestamps and now - self.timestamps[0] >= self.interval:
            self.timestamps.popleft()

    def _handle_queue(self, args, kwargs) -> Any:
        with self.lock:
            now = time.time()
            self._cleanup(now)
            
            if len(self.timestamps) < self.max_calls:
                self.timestamps.append(now)
                delay = 0
            else:
                # Обчислюємо, коли звільниться найстаріший слот
                earliest = self.timestamps[0]
                delay = self.interval - (now - earliest)
                # Бронюємо слот на майбутнє
                execution_time = now + delay
                self.timestamps.append(execution_time)
                
        if delay > 0:
            time.sleep(delay)
            
        return self.fn(*args, **kwargs)

    def _handle_drop(self, args, kwargs) -> Any:
        with self.lock:
            now = time.time()
            self._cleanup(now)

            if len(self.timestamps) < self.max_calls:
                if self.trailing_timer:
                    self.trailing_timer.cancel()
                    self.trailing_timer = None

                if self.leading:
                    self.timestamps.append(now)
                    return self.fn(*args, **kwargs)
                else:
                    self.last_args, self.last_kwargs = args, kwargs
                    self._schedule_trailing(self.interval)
                    return None
            else:
                if self.trailing:
                    self.last_args, self.last_kwargs = args, kwargs
                    if not self.trailing_timer:
                        delay = self.interval - (now - self.timestamps[0])
                        self._schedule_trailing(delay)
                return None

    def _schedule_trailing(self, delay: float):
        self.trailing_timer = threading.Timer(delay, self._execute_trailing)
        self.trailing_timer.start()

    def _execute_trailing(self):
        with self.lock:
            now = time.time()
            self.timestamps.append(now)
            args, kwargs = self.last_args, self.last_kwargs
            self.trailing_timer = None
        self.fn(*args, **kwargs)