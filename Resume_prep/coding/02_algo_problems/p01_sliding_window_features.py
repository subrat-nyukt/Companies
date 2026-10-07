"""
=============================================================
P01 — Sliding Window: Compute Rolling Features
=============================================================
ML Context:
  In credit risk & fraud detection, rolling features are critical:
  - avg_earnings_7d, cancel_rate_30d, hard_brakes_1m
  These MUST be computed efficiently on large transaction logs.

Problem:
  Given a list of daily earnings for a driver, compute the
  rolling average for every window of size k.

  Input:  earnings = [100, 200, 150, 300, 250, 400, 180]
          k = 3
  Output: [150.0, 216.67, 233.33, 316.67, 276.67]

Brute Force: O(n * k)
Optimal:     O(n)  — sliding window sum trick

Interview Tip: This directly maps to your Postpay work.
  "At Postpay, I computed 30-day rolling earnings, 
   cancellation rates, and hard-brake counts as features. 
   In PySpark, I used window functions — same concept."
=============================================================
"""

from collections import deque


# ──────────────────────────────────────────────────────────────
# SOLUTION 1: Brute Force  O(n * k) — state this first, then optimize
# ──────────────────────────────────────────────────────────────
def rolling_avg_brute(earnings: list[float], k: int) -> list[float]:
    """Compute rolling average of size k. O(n*k) time."""
    if not earnings or k > len(earnings):
        return []

    result = []
    for i in range(len(earnings) - k + 1):
        window = earnings[i : i + k]
        result.append(round(sum(window) / k, 2))
    return result


# ──────────────────────────────────────────────────────────────
# SOLUTION 2: Optimal Sliding Window  O(n) time, O(1) extra space
# ──────────────────────────────────────────────────────────────
def rolling_avg_optimal(earnings: list[float], k: int) -> list[float]:
    """
    Sliding window: maintain a running sum.
    Add the new element, subtract the element leaving the window.
    Avoids recomputing the sum from scratch each time.
    """
    if not earnings or k > len(earnings):
        return []

    window_sum = sum(earnings[:k])   # initialize first window
    result = [round(window_sum / k, 2)]

    for i in range(k, len(earnings)):
        window_sum += earnings[i]        # add new element
        window_sum -= earnings[i - k]   # remove element leaving window
        result.append(round(window_sum / k, 2))

    return result


# ──────────────────────────────────────────────────────────────
# EXTENSION: Rolling Max (useful for anomaly detection)
# "Was today's earnings the highest in the last 7 days?"
# ──────────────────────────────────────────────────────────────
def rolling_max(earnings: list[float], k: int) -> list[float]:
    """
    Monotonic deque approach: O(n) time.
    Deque stores indices; front is always the max of current window.
    """
    if not earnings or k > len(earnings):
        return []

    dq = deque()       # stores indices; front = index of current window max
    result = []

    for i, val in enumerate(earnings):
        # Remove indices outside the window
        while dq and dq[0] < i - k + 1:
            dq.popleft()

        # Remove smaller elements — they can never be the max
        while dq and earnings[dq[-1]] < val:
            dq.pop()

        dq.append(i)

        if i >= k - 1:               # window is full
            result.append(earnings[dq[0]])

    return result


# ──────────────────────────────────────────────────────────────
# EXTENSION: Multiple rolling features at once (production pattern)
# ──────────────────────────────────────────────────────────────
def compute_rolling_features(earnings: list[float], k: int) -> list[dict]:
    """
    Real-world pattern: compute avg, max, min, std in one pass.
    Returns a list of feature dicts — one per time step.
    """
    import statistics

    if not earnings or k > len(earnings):
        return []

    features = []
    for i in range(k - 1, len(earnings)):
        window = earnings[i - k + 1 : i + 1]
        features.append({
            "window_end_idx":  i,
            f"avg_{k}d":       round(sum(window) / k, 2),
            f"max_{k}d":       max(window),
            f"min_{k}d":       min(window),
            f"std_{k}d":       round(statistics.stdev(window), 2) if k > 1 else 0.0,
            f"sum_{k}d":       round(sum(window), 2),
        })
    return features


# ──────────────────────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    earnings = [100, 200, 150, 300, 250, 400, 180]
    k = 3

    print("=" * 55)
    print("P01 — Sliding Window Rolling Features")
    print("=" * 55)
    print(f"Earnings: {earnings}")
    print(f"Window k: {k}\n")

    # Basic rolling average
    brute  = rolling_avg_brute(earnings, k)
    optimal = rolling_avg_optimal(earnings, k)
    print(f"Brute Force  (O(n*k)):  {brute}")
    print(f"Optimal      (O(n)):    {optimal}")
    assert brute == optimal, "Results must match!"
    print("[OK] Results match\n")

    # Rolling max
    r_max = rolling_max(earnings, k)
    print(f"Rolling Max  (O(n)):    {r_max}")

    # Full feature set
    print("\nFull Rolling Feature Table:")
    features = compute_rolling_features(earnings, k)
    for f in features:
        print(f)

    # Edge cases
    print("\nEdge Cases:")
    print(f"Empty list: {rolling_avg_optimal([], 3)}")          # []
    print(f"k > len:    {rolling_avg_optimal([1, 2], 5)}")      # []
    print(f"k == 1:     {rolling_avg_optimal([1, 2, 3], 1)}")   # [1.0, 2.0, 3.0]

    print("\n" + "=" * 55)
    print("Complexity Summary:")
    print("  rolling_avg_brute:   Time O(n*k)  | Space O(k)")
    print("  rolling_avg_optimal: Time O(n)    | Space O(1)")
    print("  rolling_max:         Time O(n)    | Space O(k) [deque]")
