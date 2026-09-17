import unittest
import time
from circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitBreakerTimeoutException

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker(
            failure_threshold=2,
            half_open_max_calls=2,
            open_state_duration=0.5,
            timeout_per_call=0.2
        )

    def test_transition_to_open_on_failures(self):
        """Перевірка: Перехід у стан Open після досягнення ліміту помилок"""
        def failing_fn():
            raise ValueError("Service Failure")

        with self.assertRaises(ValueError):
            self.cb.call(failing_fn)
        self.assertEqual(self.cb.state(), "Closed") 
        
        with self.assertRaises(ValueError):
            self.cb.call(failing_fn)
        self.assertEqual(self.cb.state(), "Open") 

    def test_blocking_calls_in_open(self):
        """Перевірка: Блокування викликів у стані Open до закінчення тайм-ауту"""
        def failing_fn():
            raise ValueError("Error")
        def success_fn():
            return "OK"

        try: self.cb.call(failing_fn)
        except ValueError: pass
        try: self.cb.call(failing_fn)
        except ValueError: pass

        self.assertEqual(self.cb.state(), "Open")
        
        with self.assertRaises(CircuitBreakerOpenException):
            self.cb.call(success_fn)

    def test_half_open_recovery_success(self):
        """Перевірка: Поведінка HalfOpen - успішне відновлення до стану Closed"""
        def failing_fn():
            raise ValueError("Error")
        def success_fn():
            return "OK"

        try: self.cb.call(failing_fn)
        except ValueError: pass
        try: self.cb.call(failing_fn)
        except ValueError: pass
        
        time.sleep(0.6)
        self.assertEqual(self.cb.state(), "HalfOpen")
        
        self.cb.call(success_fn)
        self.assertEqual(self.cb.state(), "HalfOpen")
        self.cb.call(success_fn)
        
        self.assertEqual(self.cb.state(), "Closed")

    def test_half_open_failure_back_to_open(self):
        """Перевірка: Поведінка HalfOpen - повернення в Open при повторній помилці"""
        def failing_fn():
            raise ValueError("Error")
        
        try: self.cb.call(failing_fn)
        except ValueError: pass
        try: self.cb.call(failing_fn)
        except ValueError: pass
        
        time.sleep(0.6)
        self.assertEqual(self.cb.state(), "HalfOpen")
        
        with self.assertRaises(ValueError):
            self.cb.call(failing_fn)
            
        self.assertEqual(self.cb.state(), "Open")

    def test_call_timeout(self):
        """Перевірка: Врахування тайм-ауту окремого виклику"""
        def slow_fn():
            time.sleep(0.5)
            return "Too late"

        with self.assertRaises(CircuitBreakerTimeoutException):
            self.cb.call(slow_fn)
            
        self.assertEqual(self.cb.state(), "Closed")
        
        with self.assertRaises(CircuitBreakerTimeoutException):
            self.cb.call(slow_fn)
            
        self.assertEqual(self.cb.state(), "Open")

if __name__ == '__main__':
    unittest.main(verbosity=2)