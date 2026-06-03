"""
Routers Package - MLOps Platform API

Available routers:
- inference: Single and batch predictions
- models: Model registry and retraining
- feedback: Feedback collection for model improvement
- drift: Data drift detection
- monitoring: Health checks and metrics
"""

from api.routers import inference
from api.routers import models
from api.routers import feedback
from api.routers import drift
from api.routers import monitoring

__all__ = [
    "inference",
    "models",
    "feedback",
    "drift",
    "monitoring",
]