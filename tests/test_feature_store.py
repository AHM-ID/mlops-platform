import os
import sys
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.feature_store import FeatureStore, get_cached_features, cache_features, clear_cache
from shared.config import DATA_PATH

class TestFeatureStore:

    def test_prepare_for_training(self):
        df = pd.read_csv(DATA_PATH)
        X, y, columns = FeatureStore.prepare(df, training=True)
        
        assert X.shape[0] == df.shape[0] - df.isnull().sum().sum()
        assert y.shape[0] == X.shape[0]
        assert len(columns) > 0
        assert "Churn" not in X.columns
        assert all(col in [0, 1] for col in y.unique())

    def test_prepare_for_inference(self):
        df = pd.read_csv(DATA_PATH).head(10)
        df = df.drop(columns=["customerID", "Churn"])
        
        _, _, training_columns = FeatureStore.prepare(pd.read_csv(DATA_PATH), training=True)
        X = FeatureStore.prepare(df, training=False, columns=training_columns)
        
        assert X.shape[1] == len(training_columns)
        assert all(col in X.columns for col in training_columns)

    def test_feature_encoding_consistency(self):
        df1 = pd.read_csv(DATA_PATH).head(100)
        df2 = pd.read_csv(DATA_PATH).head(100)
        
        X1, _, cols1 = FeatureStore.prepare(df1, training=True)
        X2 = FeatureStore.prepare(df2, training=False, columns=cols1)
        
        assert X1.shape[1] == X2.shape[1]

    def test_dropna_removes_invalid_rows(self):
        df = pd.read_csv(DATA_PATH)
        original_len = len(df)
        
        X, y, _ = FeatureStore.prepare(df, training=True)
        
        assert len(X) <= original_len

    def test_total_charges_conversion(self):
        df = pd.read_csv(DATA_PATH)
        df.loc[0, "TotalCharges"] = "invalid_value"
        
        X, y, _ = FeatureStore.prepare(df, training=True)
        
        assert X["TotalCharges"].iloc[0] != "invalid_value"