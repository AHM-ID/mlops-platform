"""
Routers Package
Export all routers for API
"""

from api.routers import health
from api.routers import predictions
from api.routers import models
from api.routers import batch_jobs
from api.routers import monitoring

__all__ = [
    "health",
    "predictions",
    "models",
    "batch_jobs",
    "monitoring",
]