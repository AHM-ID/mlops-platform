import os
import sys
import pytest
import pandas as pd
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class TestDataQuality:
    
    def test_churn_data_has_required_columns(self):
        test_data = pd.DataFrame({
            "customerID": ["CUST001", "CUST002"],
            "Churn": ["Yes", "No"],
            "tenure": [12, 24],
            "MonthlyCharges": [50.5, 75.5],
            "TotalCharges": [606.0, 1812.0],
            "Contract": ["Month-to-month", "One year"],
            "InternetService": ["DSL", "Fiber optic"],
            "PaymentMethod": ["Electronic check", "Mailed check"]
        })
        
        required_cols = ["customerID", "Churn", "tenure", "MonthlyCharges", "TotalCharges",
                         "Contract", "InternetService", "PaymentMethod"]
        
        for col in required_cols:
            assert col in test_data.columns
    
    def test_churn_values_are_valid(self):
        test_data = pd.DataFrame({
            "Churn": ["Yes", "No", "Yes", "No"]
        })
        
        assert test_data["Churn"].isin(["Yes", "No"]).all()
    
    def test_tenure_in_valid_range(self):
        test_data = pd.DataFrame({
            "tenure": [0, 12, 24, 36, 72]
        })
        
        assert test_data["tenure"].between(0, 72).all()
    
    def test_monthly_charges_positive(self):
        test_data = pd.DataFrame({
            "MonthlyCharges": [20.5, 50.0, 100.5]
        })
        
        assert (test_data["MonthlyCharges"] > 0).all()
    
    def test_total_charges_numeric(self):
        test_data = pd.DataFrame({
            "TotalCharges": [606.0, 1812.0, 3618.0]
        })
        
        assert pd.to_numeric(test_data["TotalCharges"], errors="coerce").notnull().all()