import unittest
from unittest.mock import patch
from retry import Retry, BackoffStrategy

class NetworkError(Exception):
    pass

class FatalConfigError(Exception):
    pass

class TestRetry(unittest.TestCase):
    def test_success_first_attempt(self):
        """Перевірка: Успіх з 1-ї спроби, функція не повторюється"""
        retry = Retry(max_attempts=3, strategy=BackoffStrategy.CONSTANT, base_delay=0.1)
        
        def success_fn():
            success_fn.calls += 1
            return "OK"
        success_fn.calls = 0

        result = retry.execute(success_fn)
        
        self.assertEqual(result, "OK")
        self.assertEqual(success_fn.calls, 1)

    def test_success_nth_attempt(self):
        """Перевірка: Успіх з n-тої спроби (наприклад, з 3-ї)"""
        retry = Retry(
            max_attempts=4, 
            strategy=BackoffStrategy.CONSTANT, 
            base_delay=0.01,
            retry_on=(NetworkError,)
        )
        
        def flaky_fn():
            flaky_fn.calls += 1
            if flaky_fn.calls < 3:
                raise NetworkError("Temporary drop")
            return "Done"
        flaky_fn.calls = 0

        result = retry.execute(flaky_fn)
        
        self.assertEqual(result, "Done")
        self.assertEqual(flaky_fn.calls, 3)

    @patch('time.sleep', return_value=None)
    def test_stop_after_max_attempts_and_check_delays(self, mock_sleep):
        """Перевірка: Стоп після maxAttempts та правильна сума затримок (Exponential)"""
        retry = Retry(
            max_attempts=4, 
            strategy=BackoffStrategy.EXPONENTIAL, 
            base_delay=1.0,
            retry_on=(NetworkError,)
        )
        
        def failing_fn():
            failing_fn.calls += 1
            raise NetworkError("Always fails")
        failing_fn.calls = 0

        # Очікуємо, що на 4-й спробі вилетить виняток
        with self.assertRaises(NetworkError):
            retry.execute(failing_fn)
            
        self.assertEqual(failing_fn.calls, 4)
        
        # Для 4 спроб має бути рівно 3 паузи
        self.assertEqual(mock_sleep.call_count, 3)
        
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertEqual(delays, [1.0, 2.0, 4.0]) # 1.0 * 2^0, 1.0 * 2^1, 1.0 * 2^2
        self.assertEqual(sum(delays), 7.0)

    def test_no_retry_on_non_retryable_error(self):
        """Перевірка: Не повторюємо на non-retryable помилках"""
        retry = Retry(
            max_attempts=5, 
            strategy=BackoffStrategy.CONSTANT, 
            base_delay=0.1,
            retry_on=(NetworkError,) # Ретрай лише для NetworkError
        )
        
        def fatal_fn():
            fatal_fn.calls += 1
            raise FatalConfigError("This is fatal")
        fatal_fn.calls = 0

        with self.assertRaises(FatalConfigError):
            retry.execute(fatal_fn)
            
        # Має впасти одразу після першої ж спроби, без повторів
        self.assertEqual(fatal_fn.calls, 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)