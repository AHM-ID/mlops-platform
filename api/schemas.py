"""
Request/Response schemas with Pydantic for FastAPI
Provides data validation and OpenAPI documentation
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class PredictionRequest(BaseModel):
    customer_id: Optional[str] = Field(None, description="Unique customer identifier")
    tenure: int = Field(..., ge=0, description="Tenure in months")
    MonthlyCharges: float = Field(..., gt=0, description="Monthly charges in currency")
    TotalCharges: float = Field(..., ge=0, description="Total charges to date")
    Contract: str = Field(..., description="Contract type: Month-to-month, One year, Two year")
    InternetService: str = Field(..., description="Internet service type: Fiber optic, DSL, No")
    PaymentMethod: str = Field(..., description="Payment method")

    @validator('Contract')
    def validate_contract(cls, v):
        allowed = ['Month-to-month', 'One year', 'Two year']
        if v not in allowed:
            raise ValueError(f'Contract must be one of: {allowed}')
        return v

    @validator('InternetService')
    def validate_internet_service(cls, v):
        allowed = ['Fiber optic', 'DSL', 'No']
        if v not in allowed:
            raise ValueError(f'InternetService must be one of: {allowed}')
        return v

    @validator('PaymentMethod')
    def validate_payment_method(cls, v):
        allowed = ['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)']
        if v not in allowed:
            raise ValueError(f'PaymentMethod must be one of: {allowed}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "CUST001",
                "tenure": 24,
                "MonthlyCharges": 75.5,
                "TotalCharges": 1814.0,
                "Contract": "Two year",
                "InternetService": "Fiber optic",
                "PaymentMethod": "Electronic check"
            }
        }


class PredictionResponse(BaseModel):
    customer_id: Optional[str] = Field(None, description="Customer identifier echo")
    prediction: int = Field(..., ge=0, le=1, description="Churn prediction: 0 (no churn), 1 (churn)")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of churn")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage")
    model_version: str = Field(..., description="Model version used for prediction")
    prediction_id: str = Field(default="", description="ID for submitting feedback")

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "CUST001",
                "prediction": 1,
                "probability": 0.75,
                "confidence": 75.0,
                "model_version": "1",
                "prediction_id": "pred_abc123"
            }
        }


class BatchPredictionRequest(BaseModel):
    data: List[PredictionRequest] = Field(..., description="List of customer records to predict")
    batch_name: Optional[str] = Field(None, description="Human-readable batch name")

    class Config:
        json_schema_extra = {
            "example": {
                "batch_name": "Monthly_Churn_Predictions_Jan2024",
                "data": [
                    {
                        "customer_id": "CUST001",
                        "tenure": 24,
                        "MonthlyCharges": 75.5,
                        "TotalCharges": 1814.0,
                        "Contract": "Two year",
                        "InternetService": "Fiber optic",
                        "PaymentMethod": "Electronic check"
                    }
                ]
            }
        }


class BatchPredictionResponse(BaseModel):
    batch_id: str = Field(..., description="Unique batch job ID")
    status: str = Field(..., description="Job status: submitted, processing, completed, failed")
    total_records: int = Field(..., description="Total records submitted")
    celery_task_id: str = Field(..., description="Celery task ID for tracking")
    created_at: datetime = Field(..., description="Batch creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_20240115_abc123",
                "status": "submitted",
                "total_records": 1000,
                "celery_task_id": "1f3d2e4a-5c6b-7d8e-9f0a-1b2c3d4e5f6a",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }

class CollectTrainingDataResponse(BaseModel):
    status: str
    message: str

class DriftCheckDetail(BaseModel):
    run_id: str
    timestamp: Any
    dataset_drift: bool

class DriftStatusResponse(BaseModel):
    recent_checks: List[DriftCheckDetail]
    status: str

class TriggerRetrainResponse(BaseModel):
    status: str
    task_id: str
    message: str

class ModelMetadata(BaseModel):
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    stage: str = Field(..., description="Model stage: None, Staging, Production, Archived")
    created_date: datetime = Field(..., description="Model creation date")
    last_updated: datetime = Field(..., description="Last update timestamp")
    metrics: Dict[str, float] = Field(..., description="Model performance metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer-churn-model",
                "version": "3",
                "stage": "Production",
                "created_date": "2024-01-10T08:00:00Z",
                "last_updated": "2024-01-15T10:30:00Z",
                "metrics": {
                    "accuracy": 0.85,
                    "precision": 0.82,
                    "recall": 0.79,
                    "f1_score": 0.80,
                    "auc": 0.88
                }
            }
        }


class ModelListResponse(BaseModel):
    production: Optional[ModelMetadata] = Field(None, description="Production model")
    staging: Optional[ModelMetadata] = Field(None, description="Staging model")
    all_versions: List[ModelMetadata] = Field(..., description="All available versions")


class ModelDeployRequest(BaseModel):
    model_name: str = Field(..., description="Model name in MLflow registry")
    version: str = Field(..., description="Model version to deploy")
    target_stage: str = Field(..., description="Target stage: Staging or Production")

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "customer-churn-model",
                "version": "4",
                "target_stage": "Production"
            }
        }


class ModelDeployResponse(BaseModel):
    success: bool
    model_name: str
    version: str
    target_stage: str
    message: str


class BatchJobStatus(BaseModel):
    batch_id: str = Field(..., description="Batch job ID")
    status: str = Field(..., description="Status: submitted, processing, completed, failed")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    total_records: int = Field(..., description="Total records in batch")
    processed_records: int = Field(..., description="Records processed so far")
    created_at: datetime = Field(..., description="Job submission time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    celery_task_id: str = Field(..., description="Celery task ID")

    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_20240115_abc123",
                "status": "processing",
                "progress": 45,
                "total_records": 1000,
                "processed_records": 450,
                "created_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:31:00Z",
                "completed_at": None,
                "celery_task_id": "1f3d2e4a-5c6b-7d8e-9f0a-1b2c3d4e5f6a"
            }
        }


class BatchResultsSummary(BaseModel):
    batch_id: str
    total_records: int
    churn_predictions: int
    no_churn_predictions: int
    churn_rate: float = Field(..., ge=0.0, le=1.0)
    average_churn_probability: float = Field(..., ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_20240115_abc123",
                "total_records": 1000,
                "churn_predictions": 250,
                "no_churn_predictions": 750,
                "churn_rate": 0.25,
                "average_churn_probability": 0.35
            }
        }


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float
    label: Optional[str] = None


class APIMetrics(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    average_response_time_ms: float
    requests_per_second: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 10000,
                "successful_requests": 9950,
                "failed_requests": 50,
                "error_rate": 0.005,
                "average_response_time_ms": 45.2,
                "requests_per_second": 10.5
            }
        }


class SystemHealth(BaseModel):
    status: str = Field(..., description="Overall status: healthy/degraded/critical")
    timestamp: datetime
    mlflow_connected: bool
    postgres_connected: bool
    redis_connected: bool
    disk_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_percent: float = Field(..., ge=0, le=100)
    cpu_usage_percent: float = Field(..., ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "mlflow_connected": True,
                "postgres_connected": True,
                "redis_connected": True,
                "disk_usage_percent": 45.5,
                "memory_usage_percent": 62.3,
                "cpu_usage_percent": 28.1
            }
        }

class HealthStatus(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status: healthy/unhealthy")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")
    services: Dict[str, str] = Field(..., description="Status of dependencies")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "3.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "mlflow": "connected",
                    "postgres": "connected",
                    "redis": "connected"
                }
            }
        }


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for debugging")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Batch job not found",
                "error_code": "BATCH_NOT_FOUND",
                "details": {"batch_id": "invalid_id"},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }