"""
=============================================================
P04 — LRU Cache: Feature Store Caching Layer
=============================================================
ML Context:
  In a real-time ML serving system, fetching features from
  a database for every prediction is too slow.
  Solution: LRU (Least Recently Used) cache in front of the DB.

  - Most recently requested driver features stay in cache
  - Least recently used features get evicted when cache is full
  - Reduces DB calls by 80-90% in a typical fraud scoring system

Problem:
  Implement an LRU Cache with O(1) get and O(1) put.
  capacity = 3 (can hold 3 driver feature sets)

  put("DRV_001", {...features})  # cache: [DRV_001]
  put("DRV_002", {...features})  # cache: [DRV_001, DRV_002]
  put("DRV_003", {...features})  # cache: [DRV_001, DRV_002, DRV_003]
  get("DRV_001")                 # cache: [DRV_002, DRV_003, DRV_001]
  put("DRV_004", {...features})  # evict DRV_002 → [DRV_003, DRV_001, DRV_004]

Key Insight: Use a dict + doubly linked list for O(1) ops.
  - Dict: O(1) lookup (key → node)
  - Doubly linked list: O(1) move-to-front and evict-from-back

Interview Tip:
  "The feature store at Postpay pre-computed RFM features 
   nightly and cached them. For real-time serving, we'd hit 
   Redis first — Redis is essentially an LRU cache. This 
   question tests whether you understand that implementation."
=============================================================
"""


# ──────────────────────────────────────────────────────────────
# Doubly Linked List Node
# ──────────────────────────────────────────────────────────────
class Node:
    """Each node holds a key-value pair and links to neighbors."""
    def __init__(self, key=None, value=None):
        self.key   = key
        self.value = value
        self.prev  = None
        self.next  = None


# ──────────────────────────────────────────────────────────────
# LRU Cache — O(1) get and put
# ──────────────────────────────────────────────────────────────
class LRUFeatureCache:
    """
    LRU Cache using dict + doubly linked list.
    
    Layout: [DUMMY_HEAD] ↔ [MRU] ↔ ... ↔ [LRU] ↔ [DUMMY_TAIL]
    - dummy_head.next = Most Recently Used
    - dummy_tail.prev = Least Recently Used (next to evict)

    Args:
        capacity: max number of driver feature sets to cache
    """

    def __init__(self, capacity: int):
        self.capacity   = capacity
        self.cache      = {}            # key → Node (O(1) lookup)
        self.size       = 0

        # Sentinel nodes — avoid edge cases for empty list
        self.head = Node()  # dummy head (MRU side)
        self.tail = Node()  # dummy tail (LRU side)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: Node) -> None:
        """Remove a node from its current position in the list. O(1)"""
        prev_node   = node.prev
        next_node   = node.next
        prev_node.next = next_node
        next_node.prev = prev_node

    def _insert_after_head(self, node: Node) -> None:
        """Insert node right after dummy head (mark as MRU). O(1)"""
        node.prev       = self.head
        node.next       = self.head.next
        self.head.next.prev = node
        self.head.next  = node

    def get(self, key: str):
        """
        Retrieve features for a driver.
        If found: move to MRU position, return value.
        If not found: return -1 (cache miss → fetch from DB).
        Time: O(1)
        """
        if key not in self.cache:
            return -1   # Cache miss

        node = self.cache[key]
        self._remove(node)              # unlink from current position
        self._insert_after_head(node)   # move to MRU
        return node.value

    def put(self, key: str, value) -> None:
        """
        Store driver features.
        If key exists: update value and move to MRU.
        If new and cache full: evict LRU, insert new as MRU.
        Time: O(1)
        """
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._remove(node)
            self._insert_after_head(node)
        else:
            # Evict LRU if at capacity
            if self.size >= self.capacity:
                lru_node = self.tail.prev    # LRU is just before dummy tail
                self._remove(lru_node)
                del self.cache[lru_node.key]
                self.size -= 1

            # Insert new node as MRU
            new_node = Node(key, value)
            self.cache[key] = new_node
            self._insert_after_head(new_node)
            self.size += 1

    def current_order(self) -> list[str]:
        """Return keys from MRU to LRU (for debugging)."""
        result = []
        node = self.head.next
        while node != self.tail:
            result.append(node.key)
            node = node.next
        return result


# ──────────────────────────────────────────────────────────────
# Production Pattern: Cache-Aside (used in feature stores)
# ──────────────────────────────────────────────────────────────
class DriverFeatureService:
    """
    Simulates a production ML feature service with cache-aside pattern.
    
    Cache-Aside:
    1. Check cache first
    2. On miss: fetch from "DB", store in cache, return value
    """

    def __init__(self, cache_capacity: int):
        self.cache    = LRUFeatureCache(capacity=cache_capacity)
        self.db_calls = 0   # track how many times we hit the "database"

        # Simulated database of driver features
        self._db = {
            "DRV_001": {"wk_earn_3m": 1500, "cancel_rate_1m": 0.05, "bureau_score": 720},
            "DRV_002": {"wk_earn_3m": 900,  "cancel_rate_1m": 0.18, "bureau_score": 580},
            "DRV_003": {"wk_earn_3m": 2100, "cancel_rate_1m": 0.03, "bureau_score": 790},
            "DRV_004": {"wk_earn_3m": 600,  "cancel_rate_1m": 0.32, "bureau_score": 500},
        }

    def get_features(self, driver_id: str) -> dict:
        """Cache-aside: check cache → fallback to DB."""
        features = self.cache.get(driver_id)

        if features == -1:
            # Cache miss — fetch from DB
            self.db_calls += 1
            features = self._db.get(driver_id, {})
            self.cache.put(driver_id, features)
            print(f"  [DB HIT]    {driver_id} fetched from DB (total DB calls: {self.db_calls})")
        else:
            print(f"  [CACHE HIT] {driver_id} served from cache")

        return features


# ──────────────────────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("P04 — LRU Cache: Feature Store Caching Layer")
    print("=" * 55)

    # Core LRU test
    print("\n[A] Core LRU Cache (capacity=3):")
    cache = LRUFeatureCache(capacity=3)
    cache.put("DRV_001", {"score": 0.72})
    cache.put("DRV_002", {"score": 0.45})
    cache.put("DRV_003", {"score": 0.91})
    print(f"  After 3 puts:        {cache.current_order()}")  # [DRV_003, DRV_002, DRV_001]

    cache.get("DRV_001")  # DRV_001 becomes MRU
    print(f"  After get(DRV_001):  {cache.current_order()}")  # [DRV_001, DRV_003, DRV_002]

    cache.put("DRV_004", {"score": 0.55})  # DRV_002 evicted (LRU)
    print(f"  After put(DRV_004):  {cache.current_order()}")  # [DRV_004, DRV_001, DRV_003]

    print(f"  Get DRV_002 (evicted): {cache.get('DRV_002')}")  # -1 (cache miss)
    print(f"  Get DRV_001 (cached):  {cache.get('DRV_001')}")  # features dict

    # Production pattern test
    print("\n[B] Production Cache-Aside Pattern (capacity=2):")
    service = DriverFeatureService(cache_capacity=2)
    print("\n  Scoring 5 predictions:")
    service.get_features("DRV_001")  # DB miss
    service.get_features("DRV_002")  # DB miss
    service.get_features("DRV_001")  # Cache hit (saved a DB call!)
    service.get_features("DRV_003")  # DB miss → evicts DRV_002
    service.get_features("DRV_002")  # DB miss (was evicted)
    print(f"\n  Total DB calls: {service.db_calls} (vs 5 without cache)")

    print("\n" + "=" * 55)
    print("Complexity Summary:")
    print("  LRUFeatureCache.get:  Time O(1) | Space O(capacity)")
    print("  LRUFeatureCache.put:  Time O(1) | Space O(capacity)")
    print("  Cache hit rate in production typically: 80-95%")
