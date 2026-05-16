import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.config import DATA_PATH

def test_churn_data_quality():
    assert os.path.exists(DATA_PATH), f"Data file not found at {DATA_PATH}"
    df = pd.read_csv(DATA_PATH)

    required_cols = ["customerID", "Churn", "tenure", "MonthlyCharges", "TotalCharges",
                     "Contract", "InternetService", "PaymentMethod"]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    critical_cols = ["Churn", "tenure", "MonthlyCharges"]
    for col in critical_cols:
        assert df[col].isnull().sum() == 0, f"Null values found in {col}"

    assert df["Churn"].isin(["Yes", "No"]).all(), "Invalid values in Churn column"
    assert df["tenure"].between(0, 72).all(), "Tenure out of expected range (0-72)"

    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    assert df["TotalCharges"].notnull().all(), "TotalCharges contains non-numeric values"

    print("All data quality checks passed.")

if __name__ == "__main__":
    test_churn_data_quality()