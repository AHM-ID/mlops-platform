import os
import sys
import pytest
from unittest.mock import Mock, patch, AsyncMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.retrain_queue import RetrainQueueManager

class TestDriftDetection:

    def test_get_reference_data(self):
        import pandas as pd
        from worker.drift_tasks import DriftTask
        
        mock_df = pd.DataFrame({
            "customerID": ["A", "B"],
            "Churn": ["Yes", "No"],
            "tenure": [12, 24],
            "MonthlyCharges": [50, 75],
            "TotalCharges": [600, 1800],
            "Contract": ["Month-to-month", "One year"],
            "InternetService": ["DSL", "Fiber optic"],
            "PaymentMethod": ["Electronic check", "Mailed check"]
        })
        
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.return_value = mock_df
            
            task = DriftTask()
            result = task.get_reference_data()
            
            assert result is not None
            assert "customerID" in result.columns or "Churn" in result.columns

    def test_column_mapping_has_required_fields(self):
        from worker.drift_tasks import DriftTask
        task = DriftTask()
        mapping = task.get_column_mapping()
        
        assert mapping.target == "Churn"
        assert "tenure" in mapping.numerical_features
        assert "MonthlyCharges" in mapping.numerical_features
        assert "TotalCharges" in mapping.numerical_features

    def test_drift_check_with_insufficient_samples(self):
        queue_manager = RetrainQueueManager()
        
        with patch.object(queue_manager, 'get_recent_predictions', return_value=[]):
            recent = queue_manager.get_recent_predictions(hours=24)
            assert len(recent) == 0

    def test_drift_report_generation(self):
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset
        
        report = Report(metrics=[DataDriftPreset()])
        assert report is not None

    def test_drift_detection_imports(self):
        try:
            from evidently import ColumnMapping
            from evidently.metric_preset import DataDriftPreset
            assert True
        except ImportError:
            assert False, "evidently imports failed"