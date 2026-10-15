import asyncio
import unittest

from fan_in import fan_in


async def make_stream(values, delay=0):
    for value in values:
        if delay:
            await asyncio.sleep(delay)
        yield value


async def failing_stream():
    yield 1
    raise ValueError("Помилка вхідного потоку")


async def collect(stream):
    return [item async for item in stream]


class FanInTests(unittest.IsolatedAsyncioTestCase):
    async def test_merge_two_streams(self):
        result = await collect(fan_in([
            make_stream([1, 2, 3]),
            make_stream([4, 5, 6]),
        ]))

        self.assertCountEqual(result, [1, 2, 3, 4, 5, 6])
        self.assertLess(result.index(1), result.index(2))
        self.assertLess(result.index(2), result.index(3))
        self.assertLess(result.index(4), result.index(5))
        self.assertLess(result.index(5), result.index(6))

    async def test_merge_three_streams(self):
        result = await collect(fan_in([
            make_stream(["A1", "A2"]),
            make_stream(["B1", "B2"]),
            make_stream(["C1", "C2"]),
        ]))

        self.assertEqual(len(result), 6)
        for prefix in ("A", "B", "C"):
            self.assertLess(
                result.index(prefix + "1"),
                result.index(prefix + "2"),
            )

    async def test_completion_after_all_inputs(self):
        result = await asyncio.wait_for(
            collect(fan_in([
                make_stream([1], delay=0.01),
                make_stream([2], delay=0.03),
            ])),
            timeout=1,
        )
        self.assertCountEqual(result, [1, 2])

    async def test_error_does_not_block_other_streams(self):
        errors = asyncio.Queue()
        result = await asyncio.wait_for(
            collect(fan_in([
                failing_stream(),
                make_stream([10, 20, 30], delay=0.01),
            ], errors=errors)),
            timeout=1,
        )

        self.assertIn(1, result)
        self.assertIn(10, result)
        self.assertIn(20, result)
        self.assertIn(30, result)

        error = errors.get_nowait()
        self.assertIsInstance(error, ValueError)
        self.assertEqual(str(error), "Помилка вхідного потоку")

    async def test_empty_inputs(self):
        result = await asyncio.wait_for(collect(fan_in([])), timeout=1)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
