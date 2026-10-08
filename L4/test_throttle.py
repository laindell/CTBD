import unittest
import time
from throttle import Throttle

class TestThrottle(unittest.TestCase):
    def test_drop_mode_limit(self):
        """Перевірка: Віконне обмеження (drop) - при 10 викликах і ліміті 3 виконується лише 3"""
        calls = []
        
        @Throttle(max_calls=3, interval=0.1, mode='drop', leading=True).throttle
        def fast_fn():
            calls.append(time.time())

        for _ in range(10):
            fast_fn()

        self.assertEqual(len(calls), 3)

    def test_queue_mode_preserves_all(self):
        """Перевірка: Режим queue - порядок збережено, ліміт витримується, усі виклики виконуються"""
        calls = []
        
        @Throttle(max_calls=2, interval=0.1, mode='queue').throttle
        def queued_fn(x):
            calls.append(x)

        start = time.time()
        for i in range(4):
            queued_fn(i)
        elapsed = time.time() - start

        self.assertEqual(len(calls), 4)
        self.assertEqual(calls, [0, 1, 2, 3])
        # Перші 2 пройшли одразу, наступні 2 чекали щонайменше 0.1 секунди
        self.assertGreaterEqual(elapsed, 0.1)

    def test_trailing_mode(self):
        """Перевірка: Режим trailing - останній відкинутий виклик виконується після завершення паузи"""
        calls = []
        
        @Throttle(max_calls=1, interval=0.2, mode='drop', leading=True, trailing=True).throttle
        def trail_fn(x):
            calls.append(x)

        trail_fn(1) # Leading -> виконається одразу
        trail_fn(2) # Перевищення ліміту -> відкинуто, але збережено як trailing
        trail_fn(3) # Перевищення ліміту -> перезапише 2, збережено як trailing
        
        self.assertEqual(calls, [1])
        time.sleep(0.3) # Очікуємо спрацювання таймера
        self.assertEqual(calls, [1, 3])

    def test_leading_false_mode(self):
        """Перевірка: Режим leading=False - перший виклик відкладається і виконується в кінці вікна"""
        calls = []
        
        @Throttle(max_calls=1, interval=0.2, mode='drop', leading=False, trailing=True).throttle
        def non_leading_fn(x):
            calls.append(x)

        non_leading_fn(1)
        self.assertEqual(calls, []) # Одразу не виконується
        
        time.sleep(0.3)
        self.assertEqual(calls, [1]) # Виконується після закінчення інтервалу

if __name__ == '__main__':
    unittest.main(verbosity=2)