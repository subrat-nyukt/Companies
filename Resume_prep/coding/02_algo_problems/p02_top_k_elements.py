"""
=============================================================
P02 — Heap / Top-K: Feature Importance & Anomaly Ranking
=============================================================
ML Context:
  After training, you need the Top-K most important features.
  After scoring, you need the Top-K highest-risk customers.
  Heaps give you O(n log k) instead of O(n log n) for sorting.

Problems:
  A) Find the Top-K most important features by SHAP score.
  B) Find the K-th highest fraud score in a stream.
  C) Real-time: maintain Top-K high-risk drivers as scores arrive.

Interview Tip:
  "At Postpay, after running SHAP on 111 features, I needed
   the top 20. Python's heapq.nlargest() does this in O(n log k)
   — much faster than sorting all 111 features."
=============================================================
"""

import heapq
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────
# PART A: Top-K Feature Importance
# ──────────────────────────────────────────────────────────────

def top_k_features_sort(features: dict[str, float], k: int) -> list[tuple]:
    """
    Naive: sort all features descending, take first k.
    Time: O(n log n) | Space: O(n)
    """
    return sorted(features.items(), key=lambda x: x[1], reverse=True)[:k]


def top_k_features_heap(features: dict[str, float], k: int) -> list[tuple]:
    """
    Optimal: use a min-heap of size k.
    Time: O(n log k) | Space: O(k)

    Trick: Python's heapq is a MIN-heap.
    For Top-K largest, we use heapq.nlargest() OR a manual min-heap of size k.
    """
    if not features or k <= 0:
        return []

    # heapq.nlargest internally uses a min-heap of size k
    return heapq.nlargest(k, features.items(), key=lambda x: x[1])


def top_k_features_manual_heap(features: dict[str, float], k: int) -> list[tuple]:
    """
    Manual min-heap of size k — good to demonstrate understanding.
    Heap stores (importance, feature_name).
    If new item > heap min → push and pop the min (evict smallest).
    """
    min_heap = []

    for name, importance in features.items():
        if len(min_heap) < k:
            heapq.heappush(min_heap, (importance, name))
        elif importance > min_heap[0][0]:   # better than current worst
            heapq.heapreplace(min_heap, (importance, name))  # pop min, push new

    # Return sorted descending
    return sorted([(name, imp) for imp, name in min_heap],
                  key=lambda x: x[1], reverse=True)


# ──────────────────────────────────────────────────────────────
# PART B: Kth Largest Fraud Score (streaming)
# ──────────────────────────────────────────────────────────────

class KthLargestFraudScore:
    """
    Maintain a min-heap of size k.
    The root (heap[0]) is always the K-th largest score seen so far.

    Use case: "Alert me when a score enters the top-K risk tier."
    Time: O(log k) per add | Space: O(k)
    """

    def __init__(self, k: int, initial_scores: list[float] = None):
        self.k = k
        self.heap = []
        for score in (initial_scores or []):
            self.add(score)

    def add(self, score: float) -> float:
        """Add a score; return the current K-th largest."""
        heapq.heappush(self.heap, score)
        if len(self.heap) > self.k:
            heapq.heappop(self.heap)        # evict the smallest
        return self.heap[0]                 # min of heap = k-th largest


# ──────────────────────────────────────────────────────────────
# PART C: Real-time Top-K High Risk Drivers
# ──────────────────────────────────────────────────────────────

@dataclass(order=True)
class DriverRisk:
    """Dataclass that supports heap ordering by risk_score."""
    risk_score: float
    driver_id:  str = field(compare=False)

    def __repr__(self):
        return f"Driver({self.driver_id}, score={self.risk_score:.3f})"


class TopKRiskQueue:
    """
    Maintains a live Top-K high-risk driver list.
    When a new score arrives, insert if it beats the current minimum.
    """

    def __init__(self, k: int):
        self.k = k
        self.min_heap: list[DriverRisk] = []   # min-heap: weakest of top-k at root

    def update(self, driver_id: str, risk_score: float) -> None:
        """Insert driver if score is high enough to enter Top-K."""
        driver = DriverRisk(risk_score=risk_score, driver_id=driver_id)
        if len(self.min_heap) < self.k:
            heapq.heappush(self.min_heap, driver)
        elif risk_score > self.min_heap[0].risk_score:
            heapq.heapreplace(self.min_heap, driver)

    def get_top_k(self) -> list[DriverRisk]:
        """Return Top-K sorted descending by risk score."""
        return sorted(self.min_heap, key=lambda d: d.risk_score, reverse=True)


# ──────────────────────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("P02 — Heap / Top-K")
    print("=" * 55)

    # Part A: Feature importance
    shap_scores = {
        "missed_remit_pct":   0.421,
        "bureau_score":        0.312,
        "wk_earn_3m":          0.205,
        "hard_brake_1m":       0.189,
        "debt_to_income":      0.155,
        "cancel_rate_1m":      0.134,
        "platform_tenure_mo":  0.098,
        "daily_trips_1m":      0.087,
        "loan_principal":      0.072,
        "gambling_tx_ratio":   0.045,
    }

    k = 5
    print(f"\n[A] Top-{k} features by SHAP score:")
    result_sort = top_k_features_sort(shap_scores, k)
    result_heap = top_k_features_heap(shap_scores, k)
    print(f"  Sort method:  {result_sort}")
    print(f"  Heap method:  {result_heap}")
    assert [f[0] for f in result_sort] == [f[0] for f in result_heap]
    print("  [OK] Both match")

    # Part B: Kth Largest streaming
    print(f"\n[B] K-th largest fraud score (k=3):")
    kth = KthLargestFraudScore(k=3, initial_scores=[0.2, 0.8, 0.5])
    print(f"  Initial 3rd largest: {kth.add(0.3):.2f}")  # 0.3 doesn't enter
    print(f"  After adding 0.9:   {kth.add(0.9):.2f}")   # 0.9 enters, 0.2 out → 3rd = 0.5
    print(f"  After adding 0.99:  {kth.add(0.99):.2f}")  # 3rd = 0.8

    # Part C: Real-time Top-K drivers
    print(f"\n[C] Real-time Top-3 high-risk drivers:")
    queue = TopKRiskQueue(k=3)
    scores = [
        ("DRV_001", 0.72), ("DRV_002", 0.45), ("DRV_003", 0.91),
        ("DRV_004", 0.38), ("DRV_005", 0.88), ("DRV_006", 0.95),
    ]
    for driver_id, score in scores:
        queue.update(driver_id, score)
        print(f"  After {driver_id} (score={score}): Top-3 = {queue.get_top_k()}")

    print("\n" + "=" * 55)
    print("Complexity Summary:")
    print("  top_k_features_sort:    Time O(n log n) | Space O(n)")
    print("  top_k_features_heap:    Time O(n log k) | Space O(k)")
    print("  KthLargestFraudScore:   Time O(log k)   | Space O(k)")
    print("  TopKRiskQueue.update:   Time O(log k)   | Space O(k)")
