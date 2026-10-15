import asyncio
import time
import unittest
from collections import Counter

from fan_out import FanOut


def slow_square(value):
    time.sleep(0.08)
    return value * value


class FanOutTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_workers_are_faster(self):
        async def run(workers):
            fan = FanOut(slow_square, workers)
            reader = asyncio.create_task(collect(fan))
            for value in range(4):
                await fan.submit(value)
            await fan.close()
            return await reader

        start = time.perf_counter()
        one_worker_results = await run(1)
        one_worker_time = time.perf_counter() - start

        start = time.perf_counter()
        four_worker_results = await run(4)
        four_worker_time = time.perf_counter() - start

        self.assertCountEqual(one_worker_results, [0, 1, 4, 9])
        self.assertCountEqual(four_worker_results, [0, 1, 4, 9])
        self.assertLess(four_worker_time, one_worker_time)

    async def test_each_task_processed_once(self):
        counts = Counter()

        def process(value):
            counts[value] += 1
            time.sleep(0.01)
            return value

        fan = FanOut(process, workers=3)
        reader = asyncio.create_task(collect(fan))
        for value in range(20):
            await fan.submit(value)
        await fan.close()
        results = await reader

        self.assertCountEqual(results, list(range(20)))
        self.assertEqual(counts, Counter({value: 1 for value in range(20)}))

    async def test_graceful_shutdown(self):
        fan = FanOut(lambda value: value + 1, workers=2)
        reader = asyncio.create_task(collect(fan))
        await fan.submit(1)
        await fan.submit(2)
        await fan.close()

        self.assertCountEqual(await reader, [2, 3])
        with self.assertRaises(RuntimeError):
            await fan.submit(3)

    async def test_invalid_worker_count(self):
        with self.assertRaises(ValueError):
            FanOut(lambda value: value, workers=0)


async def collect(fan):
    return [result async for result in fan.results()]


if __name__ == "__main__":
    unittest.main()
