import random
import unittest

from sharding import Sharding


class ShardingTests(unittest.TestCase):
    def test_get_after_put(self):
        store = Sharding()
        store.put("user-1", {"name": "Alex"})
        self.assertEqual(store.get("user-1"), {"name": "Alex"})
        self.assertIsNone(store.get("missing-key"))

    def test_distribution_is_reasonably_balanced(self):
        random.seed(42)
        store = Sharding(
            nodes=["shard-1", "shard-2", "shard-3", "shard-4"],
            virtual_nodes=100,
        )
        for index in range(4000):
            key = f"random-key-{random.getrandbits(64)}-{index}"
            store.put(key, index)

        counts = list(store.distribution().values())
        average = sum(counts) / len(counts)
        # Для 4000 ключів дозволяємо відхилення до 25% від середнього.
        self.assertTrue(
            all(abs(count - average) / average < 0.25 for count in counts),
            msg=f"Нерівномірний розподіл: {store.distribution()}",
        )

    def test_adding_shard_remaps_less_than_all_keys(self):
        store = Sharding(nodes=["A", "B", "C"], virtual_nodes=150)
        keys = [f"key-{i}" for i in range(1000)]
        old_owners = {key: store.locate(key) for key in keys}

        for key in keys:
            store.put(key, key)

        store.add_shard("D")
        remapped = sum(
            old_owners[key] != store.locate(key) for key in keys
        )
        fraction = remapped / len(keys)

        self.assertLess(fraction, 0.5, msg=f"Перемаплено {fraction:.1%} ключів")
        for key in keys:
            self.assertEqual(store.get(key), key)

    def test_removing_shard_preserves_values(self):
        store = Sharding(nodes=["A", "B", "C"], virtual_nodes=100)
        keys = [f"key-{i}" for i in range(300)]
        for key in keys:
            store.put(key, f"value-{key}")

        store.remove_shard("B")

        self.assertNotIn("B", store.shards)
        for key in keys:
            self.assertEqual(store.get(key), f"value-{key}")

    def test_console_distribution(self):
        store = Sharding(nodes=["A", "B"])
        store.put("one", 1)
        store.put("two", 2)
        counts = store.show_distribution()
        self.assertEqual(sum(counts.values()), 2)


if __name__ == "__main__":
    unittest.main()
