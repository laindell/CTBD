import time
import random
from enum import Enum
from typing import Callable, Any, Tuple, Type

class BackoffStrategy(Enum):
    CONSTANT = "constant"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponentialJitter"

class Retry:
    def __init__(
        self,
        max_attempts: int,
        strategy: BackoffStrategy,
        base_delay: float,
        retry_on: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        :param max_attempts: Максимальна кількість спроб (включно з першою)
        :param strategy: Стратегія затримки
        :param base_delay: Базовий час затримки у секундах
        :param retry_on: Кортеж з типів винятків, при яких дозволений повтор
        """
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.retry_on = retry_on

    def execute(self, fn: Callable, *args, **kwargs) -> Any:
        attempt = 1
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                # Якщо помилка не входить у список дозволених для ретраю — прокидаємо її далі одразу
                if not isinstance(e, self.retry_on):
                    raise e
                
                # Якщо вичерпали всі спроби — прокидаємо останню помилку
                if attempt >= self.max_attempts:
                    raise e
                
                # Розраховуємо затримку і чекаємо
                delay = self._calculate_delay(attempt)
                time.sleep(delay)
                attempt += 1

    def _calculate_delay(self, attempt: int) -> float:
        if self.strategy == BackoffStrategy.CONSTANT:
            return self.base_delay
        
        elif self.strategy == BackoffStrategy.EXPONENTIAL:
            # 1-а пауза = base_delay * 1, 2-а = base_delay * 2, 3-я = base_delay * 4
            return self.base_delay * (2 ** (attempt - 1))
        
        elif self.strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            # Додаємо рандомний шум (jitter), щоб уникнути проблеми "Thundering Herd"
            exp_delay = self.base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0, self.base_delay)
            return exp_delay + jitter
            
        return self.base_delay