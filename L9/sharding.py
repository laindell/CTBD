import hashlib
import bisect
from collections import Counter


class Sharding:
    """In-memory sharding з consistent hashing та віртуальними вузлами."""

    def __init__(self, nodes=None, virtual_nodes=100):
        if virtual_nodes < 1:
            raise ValueError("virtual_nodes має бути не менше 1")
        self.virtual_nodes = virtual_nodes
        self.shards = {name: {} for name in (nodes or ["shard-1", "shard-2", "shard-3"])}
        self._ring = []
        self._rebuild_ring()

    @staticmethod
    def _hash(value):
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        return int(digest, 16)

    def _rebuild_ring(self):
        self._ring = []
        for name in self.shards:
            for index in range(self.virtual_nodes):
                point = self._hash(f"{name}:{index}")
                self._ring.append((point, name))
        self._ring.sort()

    def _node_for(self, key):
        if not self._ring:
            raise RuntimeError("Немає доступних шард-вузлів")
        point = self._hash(key)
        index = bisect.bisect_left(self._ring, (point, ""))
        if index == len(self._ring):
            index = 0
        return self._ring[index][1]

    def put(self, key, value):
        """Записує значення у шард, визначений ключем."""
        node = self._node_for(key)
        self.shards[node][key] = value
        return node

    def get(self, key, default=None):
        """Читає значення з відповідного шарда."""
        node = self._node_for(key)
        return self.shards[node].get(key, default)

    def add_shard(self, name):
        """Додає шард і переміщує дані до нових власників ключів."""
        if name in self.shards:
            raise ValueError(f"Шард {name!r} вже існує")
        old_data = {}
        for shard_data in self.shards.values():
            old_data.update(shard_data)
        self.shards[name] = {}
        self._rebuild_ring()
        self._redistribute(old_data)

    def remove_shard(self, name):
        """Видаляє шард і перерозподіляє його дані."""
        if name not in self.shards:
            raise KeyError(name)
        if len(self.shards) == 1:
            raise ValueError("Не можна видалити останній шард")
        old_data = {}
        for shard_data in self.shards.values():
            old_data.update(shard_data)
        del self.shards[name]
        self._rebuild_ring()
        self._redistribute(old_data)

    def _redistribute(self, data):
        for shard_data in self.shards.values():
            shard_data.clear()
        for key, value in data.items():
            self.shards[self._node_for(key)][key] = value

    def distribution(self):
        """Повертає кількість ключів у кожному шарді."""
        return {name: len(data) for name, data in self.shards.items()}

    def show_distribution(self):
        """Виводить розподіл ключів у консоль."""
        counts = self.distribution()
        print("Розподіл ключів по шардах:")
        for name, count in counts.items():
            print(f"  {name}: {count} ключів")
        return counts

    def locate(self, key):
        """Показує, у якому шарді зберігатиметься ключ."""
        return self._node_for(key)
