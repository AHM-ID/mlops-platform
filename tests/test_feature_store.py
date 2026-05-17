import os
import sys
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.feature_store import FeatureStore

class TestFeatureStore:
    
    def test_prepare_for_training(self):
        data = {
            "tenure": [12, 24, 36],
            "MonthlyCharges": [50.5, 75.5, 100.5],
            "TotalCharges": [606.0, 1812.0, 3618.0],
            "Contract": ["Month-to-month", "One year", "Two year"],
            "InternetService": ["DSL", "Fiber optic", "No"],
            "PaymentMethod": ["Electronic check", "Mailed check", "Bank transfer (automatic)"],
            "Churn": ["Yes", "No", "Yes"]
        }
        df = pd.DataFrame(data)
        
        X, y, columns = FeatureStore.prepare(df, training=True)
        
        assert "Churn" not in X.columns
        assert len(y) == len(X)
        assert len(columns) > 0
        assert all(col in [0, 1] for col in y)
    
    def test_prepare_for_inference(self):
        import os
        train_data = {
            "tenure": [12, 24],
            "MonthlyCharges": [50.5, 75.5],
            "TotalCharges": [606.0, 1812.0],
            "Contract": ["Month-to-month", "One year"],
            "InternetService": ["DSL", "Fiber optic"],
            "PaymentMethod": ["Electronic check", "Mailed check"],
            "Churn": ["Yes", "No"]
        }
        train_df = pd.DataFrame(train_data)
        _, _, training_columns = FeatureStore.prepare(train_df, training=True)
        
        inference_data = {
            "tenure": [36],
            "MonthlyCharges": [100.5],
            "TotalCharges": [3618.0],
            "Contract": ["Two year"],
            "InternetService": ["No"],
            "PaymentMethod": ["Bank transfer (automatic)"]
        }
        inference_df = pd.DataFrame(inference_data)
        
        os.environ["TESTING"] = "false"
        X = FeatureStore.prepare(inference_df, training=False, columns=training_columns)
        os.environ["TESTING"] = "true"
        
        assert X.shape[1] <= len(training_columns)

    def test_categorical_encoding_consistency(self):
        import os
        data1 = {
            "tenure": [12],
            "MonthlyCharges": [50.5],
            "TotalCharges": [606.0],
            "Contract": ["Month-to-month"],
            "InternetService": ["DSL"],
            "PaymentMethod": ["Electronic check"],
            "Churn": ["Yes"]
        }
        data2 = {
            "tenure": [24],
            "MonthlyCharges": [75.5],
            "TotalCharges": [1812.0],
            "Contract": ["One year"],
            "InternetService": ["Fiber optic"],
            "PaymentMethod": ["Mailed check"],
            "Churn": ["No"]
        }
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)
        
        X1, _, cols1 = FeatureStore.prepare(df1, training=True)
        
        os.environ["TESTING"] = "false"
        X2 = FeatureStore.prepare(df2, training=False, columns=cols1)
        os.environ["TESTING"] = "true"
        
        assert X1.shape[1] == X2.shape[1]
    
    def test_dropna_removes_invalid_rows(self):
        data = {
            "tenure": [12, None, 36],
            "MonthlyCharges": [50.5, 75.5, 100.5],
            "TotalCharges": [606.0, 1812.0, 3618.0],
            "Contract": ["Month-to-month", "One year", "Two year"],
            "InternetService": ["DSL", "Fiber optic", "No"],
            "PaymentMethod": ["Electronic check", "Mailed check", "Bank transfer (automatic)"],
            "Churn": ["Yes", "No", "Yes"]
        }
        df = pd.DataFrame(data)
        original_len = len(df)
        
        X, y, _ = FeatureStore.prepare(df, training=True)
        
        assert len(X) < original_len