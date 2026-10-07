"""
=============================================================
P05 — Streaming Median: Online Model Monitoring
=============================================================
ML Context:
  In production ML monitoring, you track the MEDIAN of 
  incoming prediction scores or feature values in real-time.
  - "What is the median fraud score right now?"
  - "What is the median loan repayment delay this week?"
  You can't sort all historical data each time — too slow.

Problem:
  Design a data structure to find the running median of a 
  stream of numbers in O(log n) insert and O(1) get.

  Input stream: [0.5, 0.2, 0.8, 0.1, 0.9, 0.6]
  Medians:      [0.5, 0.35, 0.5, 0.35, 0.5, 0.55]

Key Insight: Two heaps — a max-heap for the lower half 
  and a min-heap for the upper half.
  - max_heap top = largest of the lower half
  - min_heap top = smallest of the upper half
  - Median = average of both tops (even count)
           = max_heap top (odd count)

Interview Tip:
  "At Postpay, we tracked the median fraud score of the 
   daily batch in real-time as the scoring job ran. This 
   let us spot anomalies mid-run: if the median shot up 
   from 0.15 to 0.45, we'd pause and investigate before 
   approving all the loans."
=============================================================
"""

import heapq


# ──────────────────────────────────────────────────────────────
# Streaming Median using Two Heaps
# ──────────────────────────────────────────────────────────────
class StreamingMedian:
    """
    Maintains the running median of a stream using two heaps.

    max_heap: lower half of numbers  (Python: negate for max-heap)
    min_heap: upper half of numbers  (Python: native min-heap)

    Invariant:
      len(max_heap) == len(min_heap)     (even total)
      OR
      len(max_heap) == len(min_heap) + 1 (odd total — extra goes to max_heap)

    Time: O(log n) per add | O(1) get_median | Space: O(n)
    """

    def __init__(self):
        self.max_heap = []   # lower half — store negatives for max behavior
        self.min_heap = []   # upper half

    def add(self, num: float) -> None:
        """Insert a new value and maintain the two-heap invariant."""

        # Step 1: Push to max_heap (lower half)
        heapq.heappush(self.max_heap, -num)

        # Step 2: Balance — ensure max_heap top <= min_heap top
        # (all lower-half values must be <= all upper-half values)
        if self.min_heap and (-self.max_heap[0]) > self.min_heap[0]:
            val = -heapq.heappop(self.max_heap)
            heapq.heappush(self.min_heap, val)

        # Step 3: Balance sizes — max_heap can have at most 1 more element
        if len(self.max_heap) > len(self.min_heap) + 1:
            val = -heapq.heappop(self.max_heap)
            heapq.heappush(self.min_heap, val)
        elif len(self.min_heap) > len(self.max_heap):
            val = heapq.heappop(self.min_heap)
            heapq.heappush(self.max_heap, -val)

    def get_median(self) -> float:
        """Return current median in O(1)."""
        if not self.max_heap:
            raise ValueError("No data in stream")

        if len(self.max_heap) == len(self.min_heap):
            # Even count: average of two middle values
            return (-self.max_heap[0] + self.min_heap[0]) / 2.0
        else:
            # Odd count: max_heap has one more → it holds the median
            return float(-self.max_heap[0])

    def stats(self) -> dict:
        """Return current stream statistics."""
        n = len(self.max_heap) + len(self.min_heap)
        return {
            "count":  n,
            "median": self.get_median() if n > 0 else None,
            "lower_half_max": -self.max_heap[0] if self.max_heap else None,
            "upper_half_min":  self.min_heap[0] if self.min_heap else None,
        }


# ──────────────────────────────────────────────────────────────
# Production Pattern: Real-time Score Monitor
# ──────────────────────────────────────────────────────────────
class ScoringBatchMonitor:
    """
    Monitors a batch scoring job in real-time.
    Alerts if the running median deviates from the expected baseline.

    Use case: Postpay runs 18K driver predictions nightly.
    If median score spikes mid-run → stop and investigate.
    """

    def __init__(self, baseline_median: float, alert_threshold: float = 0.15):
        self.baseline        = baseline_median
        self.alert_threshold = alert_threshold
        self.stream          = StreamingMedian()
        self.alerts          = []
        self.count           = 0

    def process_score(self, driver_id: str, score: float) -> None:
        """Process one prediction; check if median has drifted."""
        self.stream.add(score)
        self.count += 1

        current_median = self.stream.get_median()
        drift          = abs(current_median - self.baseline)

        if drift > self.alert_threshold:
            alert = {
                "at_prediction": self.count,
                "driver_id":     driver_id,
                "current_score": score,
                "running_median": round(current_median, 4),
                "baseline":      self.baseline,
                "drift":         round(drift, 4),
                "status":        "[ALERT] Median drift detected!",
            }
            self.alerts.append(alert)
            print(f"  {alert['status']} "
                  f"Median={current_median:.4f} | "
                  f"Drift={drift:.4f} after {self.count} predictions")


# ──────────────────────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("P05 — Streaming Median")
    print("=" * 55)

    # Core streaming median
    print("\n[A] Running medians for a stream of scores:")
    sm     = StreamingMedian()
    stream = [0.5, 0.2, 0.8, 0.1, 0.9, 0.6]

    for val in stream:
        sm.add(val)
        median = sm.get_median()
        print(f"  Added {val:.1f} => Running median: {median:.4f}  | {sm.stats()}")

    # Verify against brute force
    print("\n[B] Verification against sorted median:")
    sm2   = StreamingMedian()
    seen  = []
    match = True
    for val in [0.5, 0.2, 0.8, 0.1, 0.9, 0.6]:
        sm2.add(val)
        seen.append(val)
        seen_sorted = sorted(seen)
        n = len(seen_sorted)
        expected = (seen_sorted[n//2 - 1] + seen_sorted[n//2]) / 2 if n % 2 == 0 else seen_sorted[n//2]
        got      = sm2.get_median()
        status   = "[OK]" if abs(got - expected) < 1e-9 else "[FAIL]"
        print(f"  {status} n={n}: expected={expected:.4f}, got={got:.4f}")
        if abs(got - expected) >= 1e-9:
            match = False
    print(f"\n  All correct: {match}")

    # Production monitoring
    print("\n[C] Real-time Batch Scoring Monitor:")
    print("  Baseline median fraud score: 0.15")
    monitor = ScoringBatchMonitor(baseline_median=0.15, alert_threshold=0.10)

    # Simulate 10 predictions — last few are suddenly high (fraud wave!)
    predictions = [
        ("DRV_001", 0.12), ("DRV_002", 0.18), ("DRV_003", 0.10),
        ("DRV_004", 0.14), ("DRV_005", 0.16),
        ("DRV_006", 0.75), ("DRV_007", 0.82),  # fraud wave starts
        ("DRV_008", 0.79), ("DRV_009", 0.88), ("DRV_010", 0.91),
    ]
    for driver_id, score in predictions:
        monitor.process_score(driver_id, score)

    print(f"\n  Total alerts: {len(monitor.alerts)}")
    print(f"  Final median: {monitor.stream.get_median():.4f}")

    print("\n" + "=" * 55)
    print("Complexity Summary:")
    print("  StreamingMedian.add:        Time O(log n) | Space O(n)")
    print("  StreamingMedian.get_median: Time O(1)     | Space O(1)")
