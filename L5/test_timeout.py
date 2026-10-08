import unittest
import time
from timeout import with_timeout, TimeoutException

# Допоміжна функція-заглушка для імітації Retry
def simple_retry(attempts: int, fn: callable, *args, **kwargs):
    for attempt in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == attempts - 1:
                raise e

class TestTimeout(unittest.TestCase):
    
    def test_success_before_timeout(self):
        """Перевірка: Успішна операція до тайм-ауту"""
        def fast_operation():
            time.sleep(0.05)
            return "Success"
        
        result = with_timeout(fast_operation, 200)
        self.assertEqual(result, "Success")

    def test_timeout_exceeded(self):
        """Перевірка: Перевищення — повертається помилка тайм-ауту"""
        side_effect_occurred = False
        
        def slow_operation():
            nonlocal side_effect_occurred
            time.sleep(0.3)
            side_effect_occurred = True # Побічний ефект
            return "Done"
        
        with self.assertRaises(TimeoutException):
            with_timeout(slow_operation, 100)
            
        # Побічні ефекти не відбулися в межах очікування основного потоку
        self.assertFalse(side_effect_occurred)

    def test_combination_with_retry(self):
        """Перевірка: Комбінування з Retry (час очікування не множиться безконтрольно)"""
        def always_hangs():
            time.sleep(0.5)
            return "Done"

        start_time = time.time()
        
        # Робимо 3 спроби. На кожну даємо 100мс тайм-ауту.
        # Без тайм-ауту ми б чекали 1.5с (3 * 0.5с).
        # З тайм-аутом ми маємо чекати лише ~0.3с.
        with self.assertRaises(TimeoutException):
            simple_retry(3, with_timeout, always_hangs, 100)
            
        elapsed_time = time.time() - start_time
        
        # Перевіряємо, що ми не чекали 1.5 секунди
        self.assertTrue(0.3 <= elapsed_time < 0.45)

if __name__ == '__main__':
    unittest.main(verbosity=2)