import time
import logging
from typing import List, Dict

# Set up logging to monitor our latency in production
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class VectorDBClient:
    """Mocks a Vector Database like Pinecone or Milvus (Approximate Nearest Neighbors)."""
    def search(self, user_embedding: list, top_k: int = 500) -> List[str]:
        # Simulate ~20ms latency to search 50 Million SKUs
        time.sleep(0.02)
        return [f"item_{i}" for i in range(top_k)]

class FeatureStoreClient:
    """Mocks a fast in-memory Redis cluster for serving features."""
    def get_user_features(self, user_id: str) -> Dict:
        # Simulate ~5ms latency to fetch real-time session features computed by Apache Flink
        time.sleep(0.005)
        return {"user_embedding": [0.1, 0.4, 0.5], "last_category": "shoes"}

    def get_item_features(self, item_ids: List[str]) -> Dict[str, Dict]:
        # Simulate ~15ms latency to fetch inventory/price across 500 candidates via Redis Pipeline
        time.sleep(0.015)
        # We assume they are all in stock for this mock
        return {item_id: {"in_stock": True, "price_score": 0.8} for item_id in item_ids}

class RankerModelClient:
    """Mocks a heavy XGBoost or Deep Learning model running in Triton/ONNX."""
    def predict(self, user_feats: Dict, item_feats: Dict[str, Dict]) -> Dict[str, float]:
        # Simulate ~35ms inference latency 
        time.sleep(0.035)
        
        # Fake probability generation between 0.0 and 1.0
        # In reality, this calculates: P(Buy | user_features, item_features)
        scores = {}
        for item_id in item_feats.keys():
            # Generate a pseudo-random confident score based on the string name
            scores[item_id] = (hash(item_id + user_feats["last_category"]) % 100) / 100.0
            
        return scores

class RecommendationService:
    def __init__(self):
        # We dependency inject our clients
        self.vector_db = VectorDBClient()
        self.feature_store = FeatureStoreClient()
        self.ranking_model = RankerModelClient()

    def get_recommendations(self, user_id: str, top_n: int = 20) -> List[str]:
        start_time = time.time()
        
        try:
            # 1. Fetch User Session Context
            user_features = self.feature_store.get_user_features(user_id)
            
            # 2. STAGE 1: Candidate Generation (Retrieve top 500 candidates)
            candidate_ids = self.vector_db.search(
                user_embedding=user_features["user_embedding"],
                top_k=500
            )
            
            # 3. Fetch Item Features for the massive candidate pool
            item_features = self.feature_store.get_item_features(candidate_ids)
            
            # 4. STAGE 2: Heavy Ranking / Scoring
            scores = self.ranking_model.predict(user_features, item_features)
            
            # 5. Sort by probability score and slice the Top-N
            sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_items = [item[0] for item in sorted_candidates[:top_n]]
            
            total_latency = (time.time() - start_time) * 1000
            logging.info(f"Success: {top_n} Recs generated in {total_latency:.2f}ms")
            return top_items
            
        except Exception as e:
            # 6. RELIABILITY: Degraded Mode (99.9% Uptime)
            # If the ranking model times out, crashes, or Redis drops, immediately fallback.
            logging.error(f"Fallback triggered due to service failure: {e}")
            return self._get_fallback_popular_items(top_n)

    def _get_fallback_popular_items(self, top_n: int) -> List[str]:
        """A static Redis cache of top trending items. Guarantees a near instant response."""
        return [f"popular_fallback_item_{i}" for i in range(top_n)]


# === INTERVIEW TEST RUN ===
if __name__ == "__main__":
    service = RecommendationService()
    
    print("Normal Production Run:")
    recs = service.get_recommendations(user_id="user_123", top_n=5)
    print(f"Items to serve to web page: {recs}\n")
