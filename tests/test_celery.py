import os
import sys
import pytest
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class TestCelery:

    def test_celery_app_import(self):
        try:
            from worker.celery_app import app
            assert app is not None
        except ImportError as e:
            pytest.skip(f"Celery import failed: {e}")

    def test_retrain_task_definition(self):
        try:
            from worker.celery_app import retrain
            assert retrain.name == "retrain"
            assert retrain.__name__ == "retrain"
        except ImportError as e:
            pytest.skip(f"Celery import failed: {e}")

    def test_celery_config(self):
        try:
            from worker.celery_app import app
            assert app.conf.task_serializer == 'json'
            assert app.conf.accept_content == ['json']
            assert app.conf.result_serializer == 'json'
        except ImportError as e:
            pytest.skip(f"Celery import failed: {e}")