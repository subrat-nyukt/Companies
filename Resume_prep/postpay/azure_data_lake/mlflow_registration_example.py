import mlflow
import argparse
import pandas as pd
from sklearn.metrics import accuracy_score
import xgboost as xgb

def train_and_register_model(data_path, run_name="Moove_Risk_Training"):
    # 1. Start MLflow Run
    with mlflow.start_run(run_name=run_name) as run:
        
        # Load logic... 
        print("Loading data and training model...")
        
        # Mocking the model training parameters
        params = {
            "objective": "binary:logistic",
            "max_depth": 4,
            "learning_rate": 0.1
        }
        
        # Log Hyperparameters
        mlflow.log_params(params)
        
        # Mock Metrics 
        accuracy = 0.87
        roc_auc = 0.95
        
        # Log Metrics
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("roc_auc", roc_auc)
        
        # 2. Log and Register the Model
        print("Registering model to MLflow Model Registry...")
        
        # If the model name doesn't exist, it creates it.
        # If it does exist, it adds a new Version to it.
        mlflow.xgboost.log_model(
            xgb_model=None, # Replace with actual trained xgb model
            artifact_path="moove_risk_model",
            registered_model_name="Moove_Driver_Risk_Predictor" 
        )
        
        print(f"Run ID: {run.info.run_id} completed successfully.")

if __name__ == "__main__":
    train_and_register_model("dummy_path")
