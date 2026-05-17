import os
import sys
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trainer.optimize import search, SEARCH_SPACE

class TestOptimize:
    
    def test_search_space_has_required_params(self):
        assert "n_estimators" in SEARCH_SPACE
        assert "max_depth" in SEARCH_SPACE
        assert "min_samples_split" in SEARCH_SPACE
    
    def test_search_returns_dict(self):
        X = pd.DataFrame({
            "feature1": np.random.rand(100),
            "feature2": np.random.rand(100)
        })
        y = pd.Series(np.random.randint(0, 2, 100))
        
        with patch('optuna.create_study') as mock_study:
            mock_study_instance = mock_study.return_value
            mock_study_instance.optimize.return_value = None
            mock_study_instance.best_params = {"n_estimators": 100, "max_depth": 5, "min_samples_split": 4}
            
            result = search(X, y)
            
            assert isinstance(result, dict)
    
    def test_search_returns_params_in_search_space(self):
        X = pd.DataFrame({
            "feature1": np.random.rand(50),
            "feature2": np.random.rand(50)
        })
        y = pd.Series(np.random.randint(0, 2, 50))
        
        with patch('optuna.create_study') as mock_study:
            mock_study_instance = mock_study.return_value
            mock_study_instance.optimize.return_value = None
            mock_study_instance.best_params = {"n_estimators": 150, "max_depth": 7, "min_samples_split": 5}
            
            result = search(X, y)
            
            assert SEARCH_SPACE["n_estimators"][0] <= result["n_estimators"] <= SEARCH_SPACE["n_estimators"][1]
            assert SEARCH_SPACE["max_depth"][0] <= result["max_depth"] <= SEARCH_SPACE["max_depth"][1]
            assert SEARCH_SPACE["min_samples_split"][0] <= result["min_samples_split"] <= SEARCH_SPACE["min_samples_split"][1]