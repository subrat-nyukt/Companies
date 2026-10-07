"""
=============================================================
P03 — Graph BFS: Fraud Ring Detection
=============================================================
ML Context:
  Fraudsters don't work alone — they form rings:
  - Shared phone numbers, devices, or bank accounts
  - One verified user "vouches" for synthetic identities
  Graph traversal finds connected fraud communities.

Problem:
  Given a list of (user_A, user_B) sharing a device/phone,
  find all connected fraud rings (connected components).
  Then: check if a given user belongs to a known fraud ring.

  Input:  connections = [
            ("U1","U2"), ("U2","U3"),   # Ring 1: U1-U2-U3
            ("U4","U5"),                # Ring 2: U4-U5
            ("U6","U7"), ("U7","U8")    # Ring 3: U6-U7-U8
          ]
          known_fraudsters = {"U3", "U5"}

  Output: users in the same ring as a known fraudster
          are flagged as HIGH RISK.

Interview Tip:
  "At Robustrade/TruKKer, we identified fraud rings by 
   connecting users who shared the same device ID or bank 
   account. A single verified fraudster could contaminate 
   everyone in their connected component."
=============================================================
"""

from collections import defaultdict, deque


# ──────────────────────────────────────────────────────────────
# Build an adjacency list from edge pairs
# ──────────────────────────────────────────────────────────────
def build_graph(connections: list[tuple[str, str]]) -> dict[str, list[str]]:
    """
    Undirected graph: if U1 shares device with U2,
    both edges (U1→U2) and (U2→U1) are added.
    """
    graph = defaultdict(list)
    for u, v in connections:
        graph[u].append(v)
        graph[v].append(u)
    return graph


# ──────────────────────────────────────────────────────────────
# BFS: Find all connected components (fraud rings)
# ──────────────────────────────────────────────────────────────
def find_fraud_rings(graph: dict, all_users: set[str]) -> list[set[str]]:
    """
    BFS traversal to find all connected components.
    Each component is a potential fraud ring.
    Time: O(V + E) | Space: O(V)
    """
    visited = set()
    rings   = []

    for user in all_users:
        if user not in visited:
            # BFS from this unvisited user
            ring    = set()
            queue   = deque([user])
            visited.add(user)

            while queue:
                node = queue.popleft()
                ring.add(node)
                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            rings.append(ring)

    return rings


# ──────────────────────────────────────────────────────────────
# Flag high-risk users: those sharing a ring with a known fraudster
# ──────────────────────────────────────────────────────────────
def flag_high_risk_users(
    rings: list[set[str]],
    known_fraudsters: set[str]
) -> dict[str, str]:
    """
    Any user in the same connected component as a known fraudster
    is flagged HIGH_RISK.
    Others are CLEAN.
    """
    risk_labels = {}

    for ring in rings:
        # Check if this ring contains any known fraudster
        if ring & known_fraudsters:   # set intersection
            for user in ring:
                risk_labels[user] = "HIGH_RISK"
        else:
            for user in ring:
                risk_labels[user] = "CLEAN"

    return risk_labels


# ──────────────────────────────────────────────────────────────
# EXTENSION: Shortest path between two users
# (How many "hops" is U1 from a known fraudster?)
# ──────────────────────────────────────────────────────────────
def fraud_distance(graph: dict, start: str, target: str) -> int:
    """
    BFS to find shortest path (number of hops) between two users.
    Returns -1 if no connection.
    Use case: 'U1 is 2 hops from known fraudster U3 — flag as MEDIUM_RISK'
    """
    if start == target:
        return 0

    visited = {start}
    queue   = deque([(start, 0)])  # (node, distance)

    while queue:
        node, dist = queue.popleft()
        for neighbor in graph.get(node, []):
            if neighbor == target:
                return dist + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))

    return -1  # no connection found


# ──────────────────────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("P03 — Graph BFS: Fraud Ring Detection")
    print("=" * 55)

    connections = [
        ("U1", "U2"), ("U2", "U3"),          # Ring 1: U1-U2-U3
        ("U4", "U5"),                         # Ring 2: U4-U5
        ("U6", "U7"), ("U7", "U8"),           # Ring 3: U6-U7-U8
    ]
    known_fraudsters = {"U3", "U5"}

    # Build graph
    graph = build_graph(connections)
    all_users = set(u for edge in connections for u in edge)

    print(f"\nAll users: {sorted(all_users)}")
    print(f"Known fraudsters: {known_fraudsters}")

    # Find rings
    rings = find_fraud_rings(graph, all_users)
    print(f"\nConnected rings found: {len(rings)}")
    for i, ring in enumerate(rings, 1):
        print(f"  Ring {i}: {sorted(ring)}")

    # Flag risk
    risk = flag_high_risk_users(rings, known_fraudsters)
    print("\nRisk Labels:")
    for user in sorted(risk):
        label = risk[user]
        flag  = "[HIGH]" if label == "HIGH_RISK" else "[OK]  "
        print(f"  {flag} {user}: {label}")

    # Distances from U1 to fraudsters
    print("\nFraud Distance (hops from U1):")
    for fraudster in known_fraudsters:
        d = fraud_distance(graph, "U1", fraudster)
        print(f"  U1 -> {fraudster}: {d} hop(s)" if d >= 0 else f"  U1 -> {fraudster}: no connection")

    print("\n" + "=" * 55)
    print("Complexity Summary:")
    print("  build_graph:          Time O(E)     | Space O(V+E)")
    print("  find_fraud_rings BFS: Time O(V+E)   | Space O(V)")
    print("  flag_high_risk_users: Time O(V)     | Space O(V)")
    print("  fraud_distance BFS:   Time O(V+E)   | Space O(V)")
