"""
=============================================================
Facial Recognition: Hands-On Code for Interview Discussions
=============================================================
This file contains runnable implementations of the KEY CONCEPTS
you'd discuss in a technical interview about your MTCNN/FaceNet project.

Sections:
  A) Triplet Loss (core FaceNet training loss)
  B) Cosine Similarity for embedding comparison
  C) FAISS-based ANN search (scaling to 1M users)
  D) Threshold tuning: FAR vs FRR (ROC for biometrics)
  E) Liveness detection skeleton (challenge-response concept)
  F) Embedding versioning (production migration pattern)

Run: python facial_recognition_code.py
Requires: pip install numpy scikit-learn
FAISS section requires: pip install faiss-cpu
=============================================================
"""

import numpy as np
from sklearn.metrics import roc_curve
from sklearn.preprocessing import normalize


# ──────────────────────────────────────────────────────────────
# A) TRIPLET LOSS
# "Explain the Triplet Loss used in FaceNet."
# ──────────────────────────────────────────────────────────────
def triplet_loss(anchor: np.ndarray, positive: np.ndarray,
                 negative: np.ndarray, margin: float = 0.2) -> float:
    """
    FaceNet's core training objective.

    Goal:
      - d(anchor, positive) SMALL  (same person closer together)
      - d(anchor, negative) LARGE  (different people pushed apart)

    Loss = max(0, d(a,p) - d(a,n) + margin)

    If d(a,n) - d(a,p) > margin: loss = 0 (triplet already satisfied)
    Otherwise: penalize the model.

    Interview talking point:
      "The margin alpha forces the model to not just be 'a bit better'
       but to keep same-person embeddings at least `margin` units
       closer than different-person embeddings."
    """
    # L2 squared distance
    dist_ap = np.sum((anchor - positive) ** 2)  # should be small
    dist_an = np.sum((anchor - negative) ** 2)  # should be large

    loss = max(0.0, dist_ap - dist_an + margin)
    return loss


def cosine_similarity(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
    """
    Compare two L2-normalized embeddings.
    Range: -1 (opposite) to 1 (identical).
    Typical same-person threshold: > 0.75
    """
    emb_a = emb_a / (np.linalg.norm(emb_a) + 1e-8)
    emb_b = emb_b / (np.linalg.norm(emb_b) + 1e-8)
    return float(np.dot(emb_a, emb_b))


# ──────────────────────────────────────────────────────────────
# B) EMBEDDING COMPARISON & VERIFICATION DECISION
# ──────────────────────────────────────────────────────────────
class FaceVerifier:
    """
    1-to-1 face verification at the point of login.
    Compares the live embedding vs stored enrollment embedding.

    Interview talking point:
      "Verification (1:1) is simpler and faster than Identification (1:N).
       For secure onboarding/login we do 1:1. For watchlist screening
       in AML fraud, we do 1:N."
    """

    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold   # Cosine similarity threshold

    def verify(self, live_embedding: np.ndarray,
               stored_embedding: np.ndarray) -> dict:
        """Return match decision with confidence score."""
        score = cosine_similarity(live_embedding, stored_embedding)
        is_match = score >= self.threshold
        return {
            "match":      is_match,
            "score":      round(score, 4),
            "threshold":  self.threshold,
            "decision":   "VERIFIED" if is_match else "REJECTED",
        }


# ──────────────────────────────────────────────────────────────
# C) FAISS ANN SEARCH — Scaling to 1M Users (1:N Identification)
# ──────────────────────────────────────────────────────────────
def demo_faiss_search(n_users: int = 10_000, embedding_dim: int = 128):
    """
    Interview talking point:
      "Linear scan over 1M embeddings would be O(N) and take seconds.
       FAISS's HNSW or IVF-PQ index reduces this to O(log N) with
       approximate nearest neighbor search — we get results in <5ms."

    How it works:
      - IVF (Inverted File Index): Divides embedding space into `nlist`
        clusters (Voronoi cells). For each query, only search `nprobe`
        nearest clusters instead of all N.
      - PQ (Product Quantization): Compresses each 128-dim vector into
        bytes, reducing memory from 512 bytes to ~32 bytes per vector.
    """
    try:
        import faiss

        print(f"\n[C] FAISS ANN Search ({n_users:,} simulated users)")

        # Simulate user embedding database
        rng = np.random.default_rng(42)
        user_embeddings = rng.standard_normal((n_users, embedding_dim)).astype("float32")
        # L2-normalize for cosine similarity
        faiss.normalize_L2(user_embeddings)

        # Build IVF-Flat index (good for <1M vectors)
        quantizer  = faiss.IndexFlatIP(embedding_dim)   # Inner Product = cosine on normalized
        n_clusters = 100
        index      = faiss.IndexIVFFlat(quantizer, embedding_dim, n_clusters,
                                         faiss.METRIC_INNER_PRODUCT)
        index.nprobe = 10      # search 10 of the 100 clusters

        # Train and add embeddings
        index.train(user_embeddings)
        index.add(user_embeddings)

        # Query: simulated live face embedding
        query = rng.standard_normal((1, embedding_dim)).astype("float32")
        faiss.normalize_L2(query)

        # Search top-5 nearest neighbors
        scores, indices = index.search(query, k=5)
        print(f"  Top-5 matched user IDs: {indices[0].tolist()}")
        print(f"  Similarity scores:      {[round(s, 4) for s in scores[0].tolist()]}")
        print(f"  Index holds: {index.ntotal:,} embeddings")

    except ImportError:
        print("\n[C] FAISS not installed. Run: pip install faiss-cpu")
        print("    Key point: IVF index = O(log N) search vs O(N) for linear scan")


# ──────────────────────────────────────────────────────────────
# D) THRESHOLD TUNING: FAR vs FRR (Biometric ROC Analysis)
# ──────────────────────────────────────────────────────────────
def threshold_analysis():
    """
    Interview talking point:
      "In fintech onboarding, the cost of a false acceptance (a fraudster
       getting in) is catastrophically higher than the cost of a false
       rejection (a user has to retry). So we pick our threshold from the
       ROC curve to achieve FAR < 0.1%, then accept whatever FRR that gives."

    Definitions:
      FAR (False Acceptance Rate) = FP / (FP + TN) : impostor accepted
      FRR (False Rejection Rate)  = FN / (FN + TP) : genuine user rejected
      Equal Error Rate (EER)      : where FAR == FRR (system benchmark)
    """
    print("\n[D] Threshold Analysis: FAR vs FRR")

    rng = np.random.default_rng(42)
    n_genuine  = 500   # same-person pairs
    n_impostor = 500   # different-person pairs

    # Genuine pairs cluster around high similarity (~0.85)
    genuine_scores  = rng.normal(0.85, 0.08, n_genuine).clip(0, 1)
    # Impostor pairs cluster around low similarity (~0.40)
    impostor_scores = rng.normal(0.40, 0.12, n_impostor).clip(0, 1)

    # Combine: label 1 = genuine match, label 0 = impostor
    scores = np.concatenate([genuine_scores, impostor_scores])
    labels = np.concatenate([np.ones(n_genuine), np.zeros(n_impostor)])

    # ROC curve
    fpr, tpr, thresholds = roc_curve(labels, scores)
    fnr = 1 - tpr   # FRR = 1 - TPR

    # Find EER (where FPR ~= FNR)
    eer_idx = np.argmin(np.abs(fpr - fnr))
    eer      = (fpr[eer_idx] + fnr[eer_idx]) / 2

    print(f"  Equal Error Rate (EER):         {eer:.3%}")
    print(f"  EER Threshold:                  {thresholds[eer_idx]:.4f}")

    # Find threshold for FAR < 0.1% (fintech requirement)
    target_far = 0.001
    low_far_idx = np.where(fpr <= target_far)[0]
    if len(low_far_idx) > 0:
        best_idx  = low_far_idx[-1]   # highest threshold still meeting FAR budget
        chosen_t  = thresholds[best_idx]
        achieved_far = fpr[best_idx]
        achieved_frr = fnr[best_idx]
        print(f"\n  Target FAR: < {target_far:.1%}")
        print(f"  Chosen threshold:             {chosen_t:.4f}")
        print(f"  Achieved FAR (impostors in):  {achieved_far:.4%}")
        print(f"  Achieved FRR (users blocked): {achieved_frr:.3%}")
        if achieved_far > 0:
            print(f"  --> At this threshold, 1 in {int(1/achieved_far):,} impostors gets through")
        else:
            print("  --> At this threshold, 0 impostors got through the test sample")
        print(f"  --> {achieved_frr:.1%} of genuine users need to retry")


# ──────────────────────────────────────────────────────────────
# E) LIVENESS DETECTION SKELETON (challenge-response)
# ──────────────────────────────────────────────────────────────
class LivenessDetector:
    """
    Interview talking point:
      "Liveness detection is non-negotiable for a fintech use case.
       A static model without it can be spoofed with a printed photo.
       We implemented a challenge-response: the user is asked to blink
       or turn their head, and we verify the facial keypoint trajectory."

    Production approaches (ordered by security level):
      1. Challenge-Response (keypoint motion)  - simple, client-side
      2. Texture Analysis (CNN on face crop)   - detects moiré/screen edges
      3. 3D Depth Map (IR camera)              - strongest, hardware-dependent
    """

    CHALLENGES = ["blink_left", "blink_right", "turn_left", "turn_right", "smile"]

    def __init__(self):
        self.challenge = None

    def issue_challenge(self) -> str:
        """Randomly select a liveness challenge."""
        import random
        self.challenge = random.choice(self.CHALLENGES)
        return self.challenge

    def verify_response(self, landmark_sequence: list[dict]) -> dict:
        """
        Verify that the landmark trajectory matches the issued challenge.
        `landmark_sequence`: list of MTCNN landmark dicts over N frames.

        Returns: liveness verdict.
        """
        if not self.challenge or not landmark_sequence:
            return {"live": False, "reason": "No challenge or frames provided"}

        # Simplified: check for eye-closure movement (blink detection)
        if "blink" in self.challenge:
            eye_key = "left_eye" if "left" in self.challenge else "right_eye"
            # In production: compute Eye Aspect Ratio (EAR) across frames
            # EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
            # EAR < 0.2 for 2+ consecutive frames = blink confirmed
            liveness_confirmed = len(landmark_sequence) >= 5
        elif "turn" in self.challenge:
            # Check yaw angle change from head pose estimation
            liveness_confirmed = len(landmark_sequence) >= 8
        else:
            liveness_confirmed = True

        return {
            "live":      liveness_confirmed,
            "challenge": self.challenge,
            "frames":    len(landmark_sequence),
            "verdict":   "LIVE" if liveness_confirmed else "SPOOF",
        }


# ──────────────────────────────────────────────────────────────
# F) EMBEDDING VERSIONING — Production Migration Pattern
# ──────────────────────────────────────────────────────────────
class EmbeddingRegistry:
    """
    Interview talking point:
      "When we upgraded from FaceNet (128-dim) to a newer architecture
       (ArcFace, 512-dim), we couldn't simply swap the model — all
       stored embeddings would break. We used versioned embedding stores
       and a background job to re-index all 100k+ users without downtime."

    Migration strategy:
      1. Deploy new model in SHADOW mode — generate v2 embeddings alongside v1.
      2. Dual-write: new enrollments write to both v1 and v2 stores.
      3. Background job: re-generate v2 embeddings for all existing users.
      4. Cutover: once 100% re-indexed, route traffic to v2.
      5. Deprecate v1 store after 1-week validation window.
    """

    def __init__(self):
        self.stores = {}   # version -> {user_id: embedding}

    def enroll(self, user_id: str, embedding: np.ndarray, version: str = "v1"):
        """Store a user's embedding under a specific model version."""
        if version not in self.stores:
            self.stores[version] = {}
        self.stores[version][user_id] = embedding
        print(f"  Enrolled {user_id} in store [{version}]")

    def verify(self, user_id: str, live_embedding: np.ndarray,
               version: str = "v1", threshold: float = 0.75) -> dict:
        """Verify using the stored embedding of the specified model version."""
        if version not in self.stores or user_id not in self.stores[version]:
            return {"error": f"User {user_id} not enrolled in version {version}"}
        stored = self.stores[version][user_id]
        score  = cosine_similarity(live_embedding, stored)
        return {"user_id": user_id, "version": version,
                "score": round(score, 4), "match": score >= threshold}

    def migrate_user(self, user_id: str, new_embedding: np.ndarray,
                     from_v: str = "v1", to_v: str = "v2"):
        """Re-index a user's embedding to a new model version."""
        self.enroll(user_id, new_embedding, version=to_v)
        print(f"  Migrated {user_id}: [{from_v}] -> [{to_v}]")


# ──────────────────────────────────────────────────────────────
# MAIN DEMO
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Facial Recognition: Interview Code Demo")
    print("=" * 60)

    rng = np.random.default_rng(42)
    DIM = 128

    # A) Triplet Loss
    print("\n[A] Triplet Loss:")
    anchor   = rng.standard_normal(DIM)
    positive = anchor + rng.normal(0, 0.1, DIM)   # close to anchor
    negative = rng.standard_normal(DIM)             # far from anchor
    loss = triplet_loss(anchor, positive, negative, margin=0.2)
    print(f"  d(anchor, positive): {np.sum((anchor - positive)**2):.4f}")
    print(f"  d(anchor, negative): {np.sum((anchor - negative)**2):.4f}")
    print(f"  Triplet Loss:        {loss:.4f} (0.0 = satisfied, >0 = learning)")

    # B) Face Verifier
    print("\n[B] Face Verification:")
    verifier = FaceVerifier(threshold=0.75)
    user_enrolled = rng.standard_normal(DIM)   # stored at enrollment
    user_live     = user_enrolled + rng.normal(0, 0.05, DIM)  # same user, slight variation
    impostor      = rng.standard_normal(DIM)   # different person

    print(f"  Same user:  {verifier.verify(user_live, user_enrolled)}")
    print(f"  Impostor:   {verifier.verify(impostor, user_enrolled)}")

    # C) FAISS
    demo_faiss_search(n_users=10_000, embedding_dim=DIM)

    # D) FAR / FRR Threshold Analysis
    threshold_analysis()

    # E) Liveness
    print("\n[E] Liveness Detection:")
    liveness = LivenessDetector()
    challenge = liveness.issue_challenge()
    print(f"  Issued challenge: {challenge}")
    fake_landmarks = [{"left_eye": (100, 200), "right_eye": (200, 200)} for _ in range(10)]
    result = liveness.verify_response(fake_landmarks)
    print(f"  Verdict: {result}")

    # F) Embedding Versioning
    print("\n[F] Embedding Versioning:")
    registry = EmbeddingRegistry()
    v1_emb = rng.standard_normal(DIM).astype(float)
    v2_emb = rng.standard_normal(512).astype(float)  # new model = 512-dim
    registry.enroll("USR_001", v1_emb, version="v1")
    registry.migrate_user("USR_001", v2_emb, from_v="v1", to_v="v2")
    print(f"  V1 verify: {registry.verify('USR_001', v1_emb + 0.01, version='v1')}")
    print(f"  V2 verify: {registry.verify('USR_001', v2_emb + 0.01, version='v2')}")

    print("\n" + "=" * 60)
    print("  All demos complete.")
    print("=" * 60)
