import time
import concurrent.futures
from enum import Enum
from typing import Callable, Any

class CircuitBreakerState(Enum):
    CLOSED = "Closed"
    OPEN = "Open"
    HALF_OPEN = "HalfOpen"

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreakerTimeoutException(Exception):
    pass

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int,
        half_open_max_calls: int,
        open_state_duration: float,
        timeout_per_call: float
    ):
        self.failure_threshold = failure_threshold
        self.half_open_max_calls = half_open_max_calls
        self.open_state_duration = open_state_duration
        self.timeout_per_call = timeout_per_call

        self._state = CircuitBreakerState.CLOSED
        self._failures = 0
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._last_open_time = 0.0

    def state(self) -> str:
        self._check_open_expiration()
        return self._state.value

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        self._check_open_expiration()

        if self._state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenException("Circuit breaker is currently OPEN. Call blocked.")

        if self._state == CircuitBreakerState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenException("Circuit breaker is HALF_OPEN and trial limit reached.")
            self._half_open_calls += 1

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fn, *args, **kwargs)
                result = future.result(timeout=self.timeout_per_call)
            
            self._record_success()
            return result

        except concurrent.futures.TimeoutError:
            self._record_failure()
            raise CircuitBreakerTimeoutException(f"Call timed out after {self.timeout_per_call}s")
        except Exception as e:
            if isinstance(e, CircuitBreakerOpenException):
                raise
            self._record_failure()
            raise e

    def _check_open_expiration(self):
        if self._state == CircuitBreakerState.OPEN:
            if time.time() - self._last_open_time >= self.open_state_duration:
                self._transition_to_half_open()

    def _record_success(self):
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_max_calls:
                self._transition_to_closed()
        elif self._state == CircuitBreakerState.CLOSED:
            self._failures = 0

    def _record_failure(self):
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
        elif self._state == CircuitBreakerState.CLOSED:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self):
        self._state = CircuitBreakerState.OPEN
        self._last_open_time = time.time()
        self._failures = 0

    def _transition_to_half_open(self):
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_calls = 0
        self._half_open_successes = 0

    def _transition_to_closed(self):
        self._state = CircuitBreakerState.CLOSED
        self._failures = 0
        self._half_open_calls = 0
        self._half_open_successes = 0