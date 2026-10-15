import asyncio
import time
import unittest

from future import Future, all, race, submit


class FutureTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_execution(self):
        future = submit(lambda: 2 + 3)
        self.assertEqual(await future.get(timeout=1), 5)

    async def test_then_callback(self):
        future = submit(lambda: 10).then(lambda value: value * 2)
        self.assertEqual(await future.get(timeout=1), 20)

    async def test_error_propagation_and_catch(self):
        def fail():
            raise ValueError("test error")

        future = submit(fail)
        with self.assertRaisesRegex(ValueError, "test error"):
            await future.get(timeout=1)

        recovered = submit(fail).catch(lambda error: str(error))
        self.assertEqual(await recovered.get(timeout=1), "test error")

    async def test_all_waits_for_every_future(self):
        futures = [
            submit(lambda: (time.sleep(0.03), "first")[1]),
            submit(lambda: (time.sleep(0.08), "second")[1]),
        ]
        result = await all(futures)
        self.assertCountEqual(result, ["first", "second"])

    async def test_race_returns_first_completed(self):
        futures = [
            submit(lambda: (time.sleep(0.15), "slow")[1]),
            submit(lambda: (time.sleep(0.02), "fast")[1]),
        ]
        self.assertEqual(await race(futures), "fast")

    async def test_get_timeout(self):
        future = submit(lambda: (time.sleep(0.15), 42)[1])
        with self.assertRaises(asyncio.TimeoutError):
            await future.get(timeout=0.01)

        # Тайм-аут очікування не скасовує обчислення.
        self.assertEqual(await future.get(timeout=1), 42)

    async def test_result_is_set_only_once(self):
        future = Future()
        future._resolve(1)
        future._resolve(2)
        self.assertEqual(await future.get(timeout=1), 1)


if __name__ == "__main__":
    unittest.main()
