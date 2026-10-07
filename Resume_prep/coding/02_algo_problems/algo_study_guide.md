# Algorithmic Problem Solving — Study Guide for Lead ML Engineer

> Focus: Problems that directly map to ML Engineering work.
> NOT leetcode grind — targeted patterns that show up in ML system design.

---

## Top 5 Patterns to Master

| Pattern | Why It Matters in ML | Problem File |
|---------|---------------------|-------------|
| **Sliding Window** | Rolling feature computation (avg_earn_7d, cancel_rate_30d) | `p01_sliding_window_features.py` |
| **Heap / Top-K** | Feature selection, top-K recommendations, anomaly ranking | `p02_top_k_elements.py` |
| **Graph BFS/DFS** | Fraud ring detection, network-based features | `p03_graph_bfs_fraud.py` |
| **LRU Cache** | Feature store caching, model prediction caching | `p04_lru_cache_feature_store.py` |
| **Streaming Median** | Online learning statistics, monitoring percentiles | `p05_streaming_median.py` |

---

## General Problem-Solving Framework (Say This Out Loud)

### Step 1 — Understand (2 min)
- Repeat the problem back in your own words
- Ask about edge cases: empty input? negative numbers? large N?
- Ask about constraints: memory? time complexity?

### Step 2 — Examples (1 min)
- Work through a small example by hand
- Identify the pattern

### Step 3 — Approach (2 min)
- State the brute-force solution first (even if slow)
- Then optimize: "I can improve this from O(n²) to O(n) using a sliding window"

### Step 4 — Code (10-15 min)
- Write clean, readable code
- Name variables clearly (don't use `x`, `y`, `temp`)
- Add inline comments for key logic

### Step 5 — Test (3 min)
- Run through your example
- Check edge cases: empty list, single element, all same values

### Step 6 — Complexity (1 min)
- State time complexity: O(n), O(n log n), O(n²)?
- State space complexity

---

## Python Essentials for the Test

```python
# Collections you MUST know
from collections import defaultdict, Counter, deque
import heapq  # min-heap by default

# heapq operations
heap = []
heapq.heappush(heap, (priority, item))
smallest = heapq.heappop(heap)
top_k = heapq.nlargest(k, items)

# deque for sliding window
window = deque(maxlen=k)
window.append(x)  # auto-evicts oldest when full

# defaultdict for graph adjacency list
graph = defaultdict(list)
graph[u].append(v)

# Counter for frequency
counts = Counter(["a", "b", "a"])  # Counter({'a': 2, 'b': 1})
most_common = counts.most_common(3)
```

---

## Time Complexity Cheat Sheet

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Sliding window sum | O(n) | Subtract leaving, add entering |
| Heap push/pop | O(log k) | k = heap size |
| BFS/DFS | O(V + E) | V = vertices, E = edges |
| Sorting | O(n log n) | Use when order matters |
| Hash lookup | O(1) avg | dict / set in Python |
| LRU Cache get/put | O(1) | Dict + doubly-linked list |

---

## Common Mistakes to Avoid

1. **Off-by-one in sliding window**: Always check `if len(window) == k`
2. **Forgetting to handle empty input**: `if not nums: return []`
3. **Python heap is min-heap**: For max-heap, negate values: `heapq.heappush(h, -val)`
4. **BFS needs a visited set**: Or you'll loop forever on cycles
5. **Not stating complexity**: Always state it at the end
