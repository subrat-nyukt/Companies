import time
import json
import logging

"""
MOCK APACHE FLINK STREAMING PIPELINE 
In production, this runs on a cluster of servers completely detached from your Web Service.
It listens to Kafka, performs heavy math, and writes the final embedding list to Redis.
"""

logging.basicConfig(level=logging.INFO, format='%(levelname)s (Flink Job): %(message)s')

class MockRedis:
    def __init__(self):
        # Stores the User's historical embedding list
        self.users = {"user_123": [0.1, 0.4, 0.5]}
        # Stores the heavy pre-computed embeddings for the actual products
        self.item_embeddings = {"item_nike_shoes": [0.8, -0.2, 0.1]}
        
    def save_user_embedding(self, user_id: str, new_embedding: list):
        self.users[user_id] = new_embedding
        logging.info(f"Saved new embedding for {user_id} into Redis in 2ms: {new_embedding}")

class BackgroundStreamingJob:
    def __init__(self):
        self.redis = MockRedis()

    def process_kafka_event(self, kafka_message: str):
        """This function triggers the moment a user clicks on the website."""
        event = json.loads(kafka_message)
        user_id = event["user_id"]
        clicked_item = event["item_id"]
        
        logging.info(f"Picked up click event from Kafka: {user_id} clicked {clicked_item}")

        # 1. Fetch the user's old embedding and the item's embedding from our Cache
        historical_emb = self.redis.users.get(user_id, [0.0, 0.0, 0.0])
        item_emb = self.redis.item_embeddings.get(clicked_item, [0.0, 0.0, 0.0])
        
        # 2. THE MATH (Usually a neural net like SASRec running on Flink, or simple math)
        # Here we do a simple moving average: (Old Model + New Click) / 2
        logging.info("Calculating new user embedding vector...")
        new_embedding = []
        for i in range(len(historical_emb)):
            updated_value = (historical_emb[i] + item_emb[i]) / 2.0
            new_embedding.append(round(updated_value, 4))
            
        # Simulate heavy math processing time
        time.sleep(0.5) 
        
        # 3. Save purely the final LIST of numbers into Redis
        self.redis.save_user_embedding(user_id, new_embedding)

if __name__ == "__main__":
    flink_job = BackgroundStreamingJob()
    
    # Simulate a Kafka message coming in from the website tracking system
    incoming_kafka_message = '{"user_id": "user_123", "item_id": "item_nike_shoes", "action": "click"}'
    
    print("\n--- BACKGROUND PIPELINE STARTING ---")
    # This runs totally independent of the Web Server.
    # It takes 0.5 seconds to run, but that's okay because the user isn't waiting for a page to load!
    flink_job.process_kafka_event(incoming_kafka_message)
    print("--- BACKGROUND PIPELINE FINISHED ---\n")
