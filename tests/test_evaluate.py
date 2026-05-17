import os
import sys
import pytest
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trainer.evaluate import metrics

class TestEvaluate:
    
    def test_metrics_returns_all_required_keys(self):
        y_true = np.array([0, 1, 0, 1, 0])
        y_pred = np.array([0, 1, 0, 0, 1])
        y_prob = np.array([0.2, 0.8, 0.3, 0.4, 0.7])
        
        result = metrics(y_true, y_pred, y_prob)
        
        assert "accuracy" in result
        assert "precision" in result
        assert "recall" in result
        assert "f1" in result
        assert "auc" in result
    
    def test_accuracy_perfect_prediction(self):
        y_true = np.array([0, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 1])
        y_prob = np.array([0.1, 0.9, 0.2, 0.8])
        
        result = metrics(y_true, y_pred, y_prob)
        
        assert result["accuracy"] == 1.0
    
    def test_accuracy_worst_prediction(self):
        y_true = np.array([0, 1, 0, 1])
        y_pred = np.array([1, 0, 1, 0])
        y_prob = np.array([0.9, 0.1, 0.8, 0.2])
        
        result = metrics(y_true, y_pred, y_prob)
        
        assert result["accuracy"] == 0.0
    
    def test_precision_score(self):
        y_true = np.array([0, 1, 1, 1, 0])
        y_pred = np.array([0, 1, 0, 1, 0])
        y_prob = np.array([0.1, 0.9, 0.4, 0.8, 0.2])
        
        result = metrics(y_true, y_pred, y_prob)
        
        assert 0 <= result["precision"] <= 1
    
    def test_auc_score_range(self):
        y_true = np.array([0, 1, 0, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 1, 0, 1])
        y_prob = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7])
        
        result = metrics(y_true, y_pred, y_prob)
        
        assert 0 <= result["auc"] <= 1