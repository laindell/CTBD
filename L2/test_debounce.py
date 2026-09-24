import unittest
import time

from debounce import debounce


class Counter:
    def __init__(self):
        self.count = 0

    def inc(self):
        self.count += 1


class TestDebounce(unittest.TestCase):

    def test_fast_calls_single_execution(self):
        """Перевірка: серія швидких викликів -> єдиний виклик fn"""

        counter = Counter()

        debounced = debounce(
            counter.inc,
            delay_ms=100,
            leading=False,
            trailing=True
        )

        debounced()
        debounced()
        debounced()

        # Функція ще не повинна виконатися
        self.assertEqual(counter.count, 0)

        time.sleep(0.15)

        # Після паузи виконується тільки один виклик
        self.assertEqual(counter.count, 1)

        debounced.dispose()


    def test_leading_only(self):
        """Перевірка: leading=True -> миттєвий перший виклик"""

        counter = Counter()

        debounced = debounce(
            counter.inc,
            delay_ms=100,
            leading=True,
            trailing=False
        )

        debounced()

        # Перший виклик виконується одразу
        self.assertEqual(counter.count, 1)

        debounced()
        debounced()

        # Наступні виклики пригнічуються
        self.assertEqual(counter.count, 1)

        time.sleep(0.15)

        # Після паузи додаткового виклику немає
        self.assertEqual(counter.count, 1)

        debounced.dispose()


    def test_leading_and_trailing(self):
        """Перевірка: одночасна робота leading і trailing"""

        counter = Counter()

        debounced = debounce(
            counter.inc,
            delay_ms=100,
            leading=True,
            trailing=True
        )

        # Перший виклик виконується одразу
        debounced()

        self.assertEqual(counter.count, 1)

        # Наступні виклики відкладаються
        debounced()
        debounced()

        time.sleep(0.15)

        # Після паузи виконується останній виклик
        self.assertEqual(counter.count, 2)

        debounced.dispose()


    def test_dispose(self):
        """Перевірка: dispose() скасовує запланований виклик"""

        counter = Counter()

        debounced = debounce(
            counter.inc,
            delay_ms=100,
            leading=False,
            trailing=True
        )

        debounced()

        # Скасовуємо таймер
        debounced.dispose()

        time.sleep(0.15)

        # Функція не повинна виконатися
        self.assertEqual(counter.count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)