"""
Request/Response schemas with Pydantic for FastAPI
Provides data validation and OpenAPI documentation
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


# ============================================
# Prediction Schemas
# ============================================

class PredictionRequest(BaseModel):
    """
    Request schema for single prediction endpoint.
    
    Contains all customer features required for churn prediction.
    All categorical fields have strict validation for allowed values.
    
    Example Request:
    ```json
    {
        "customer_id": "CUST-1001",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 24,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "Yes",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "No",
        "Contract": "Two year",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 75.5,
        "TotalCharges": 1814.0
    }
    ```
    """
    customer_id: Optional[str] = Field(None, description="Unique customer identifier", example="CUST-1001")
    gender: str = Field(..., description="Customer gender", example="Female")
    SeniorCitizen: int = Field(..., ge=0, le=1, description="Senior citizen flag (0 = No, 1 = Yes)", example=0)
    Partner: str = Field(..., description="Has partner", example="Yes")
    Dependents: str = Field(..., description="Has dependents", example="No")
    tenure: int = Field(..., ge=0, le=72, description="Tenure in months (0-72)", example=24)
    PhoneService: str = Field(..., description="Has phone service", example="Yes")
    MultipleLines: str = Field(..., description="Multiple lines status", example="No")
    InternetService: str = Field(..., description="Internet service type", example="Fiber optic")
    OnlineSecurity: str = Field(..., description="Online security subscription", example="No")
    OnlineBackup: str = Field(..., description="Online backup subscription", example="Yes")
    DeviceProtection: str = Field(..., description="Device protection subscription", example="No")
    TechSupport: str = Field(..., description="Tech support subscription", example="No")
    StreamingTV: str = Field(..., description="TV streaming subscription", example="Yes")
    StreamingMovies: str = Field(..., description="Movie streaming subscription", example="No")
    Contract: str = Field(..., description="Contract type", example="Two year")
    PaperlessBilling: str = Field(..., description="Paperless billing enabled", example="Yes")
    PaymentMethod: str = Field(..., description="Payment method", example="Electronic check")
    MonthlyCharges: float = Field(..., gt=0, le=200, description="Monthly charges amount", example=75.5)
    TotalCharges: float = Field(..., ge=0, le=10000, description="Total charges to date", example=1814.0)

    @validator('gender')
    def validate_gender(cls, v):
        allowed = ['Male', 'Female']
        if v not in allowed:
            raise ValueError(f'Gender must be one of: {allowed}')
        return v

    @validator('SeniorCitizen')
    def validate_senior(cls, v):
        if v not in [0, 1]:
            raise ValueError('SeniorCitizen must be 0 or 1')
        return v

    @validator('Partner', 'Dependents', 'PhoneService', 'PaperlessBilling')
    def validate_yes_no(cls, v):
        allowed = ['Yes', 'No']
        if v not in allowed:
            raise ValueError(f'Value must be one of: {allowed}')
        return v

    @validator('MultipleLines')
    def validate_multiple_lines(cls, v):
        allowed = ['Yes', 'No', 'No phone service']
        if v not in allowed:
            raise ValueError(f'MultipleLines must be one of: {allowed}')
        return v

    @validator('InternetService')
    def validate_internet_service(cls, v):
        allowed = ['DSL', 'Fiber optic', 'No']
        if v not in allowed:
            raise ValueError(f'InternetService must be one of: {allowed}')
        return v

    @validator('OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies')
    def validate_internet_addons(cls, v):
        allowed = ['Yes', 'No', 'No internet service']
        if v not in allowed:
            raise ValueError(f'Value must be one of: {allowed}')
        return v

    @validator('Contract')
    def validate_contract(cls, v):
        allowed = ['Month-to-month', 'One year', 'Two year']
        if v not in allowed:
            raise ValueError(f'Contract must be one of: {allowed}')
        return v

    @validator('PaymentMethod')
    def validate_payment_method(cls, v):
        allowed = ['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)']
        if v not in allowed:
            raise ValueError(f'PaymentMethod must be one of: {allowed}')
        return v

    @validator('MonthlyCharges')
    def validate_monthly_charges(cls, v):
        if v <= 0 or v > 200:
            raise ValueError('MonthlyCharges must be between 0 and 200')
        return v

    @validator('TotalCharges')
    def validate_total_charges(cls, v):
        if v < 0:
            raise ValueError('TotalCharges cannot be negative')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "CUST-1001",
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 24,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": "Fiber optic",
                "OnlineSecurity": "No",
                "OnlineBackup": "Yes",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "Yes",
                "StreamingMovies": "No",
                "Contract": "Two year",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 75.5,
                "TotalCharges": 1814.0
            }
        }


class PredictionResponse(BaseModel):
    """
    Response schema for single prediction endpoint.
    
    Returns the churn prediction with probability and confidence score.
    Includes a prediction_id for submitting feedback.
    
    Example Response:
    ```json
    {
        "customer_id": "CUST-1001",
        "prediction": 0,
        "probability": 0.2347,
        "confidence": 23.47,
        "model_version": "3",
        "prediction_id": "abc123-def456-ghi789"
    }
    ```
    """
    customer_id: Optional[str] = Field(None, description="Customer identifier (echoed from request)", example="CUST-1001")
    prediction: int = Field(..., ge=0, le=1, description="Churn prediction: 0 = No churn, 1 = Churn", example=0)
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of churn (0-1)", example=0.23)
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage (probability * 100)", example=23.48)
    model_version: str = Field(..., description="Model version used for prediction", example="3")
    prediction_id: str = Field(default="", description="Unique ID for submitting feedback", example="abc123-def456-ghi789")


# ============================================
# Batch Prediction Schemas
# ============================================

class BatchPredictionRequest(BaseModel):
    """
    Request schema for batch prediction endpoint.
    
    Submits multiple customer records for asynchronous batch processing.
    Maximum 10,000 records per batch.
    
    Example Request:
    ```json
    {
        "batch_name": "January_2024_Monthly_Batch",
        "data": [<PredictionRequest objects>]
    }
    ```
    """
    batch_name: Optional[str] = Field(None, description="Human-readable batch name for identification", example="January_2024_Monthly_Batch")
    data: List[PredictionRequest] = Field(..., description="List of customer records to predict (max 10,000)", min_items=1, max_items=10000)


class BatchPredictionResponse(BaseModel):
    """
    Response schema for batch prediction submission.
    
    Returns a batch_id for tracking the asynchronous job.
    
    Example Response:
    ```json
    {
        "batch_id": "batch_20240115_abc123",
        "status": "submitted",
        "total_records": 1000,
        "celery_task_id": "1f3d2e4a-5c6b-7d8e-9f0a-1b2c3d4e5f6a",
        "created_at": "2024-01-15T10:30:00Z"
    }
    ```
    """
    batch_id: str = Field(..., description="Unique batch job ID for status tracking")
    status: str = Field(..., description="Job status: submitted, processing, completed, failed")
    total_records: int = Field(..., description="Total records submitted for processing")
    celery_task_id: str = Field(..., description="Celery task ID for advanced tracking")
    created_at: datetime = Field(..., description="Batch creation timestamp (UTC)")


class BatchJobStatus(BaseModel):
    """
    Status information for a batch job.
    
    Provides progress tracking and timing information.
    """
    batch_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    total_records: int
    processed_records: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    celery_task_id: str


class BatchResultsSummary(BaseModel):
    """
    Aggregated summary statistics for a completed batch.
    
    Example Response:
    ```json
    {
        "batch_id": "batch_20240115_abc123",
        "total_records": 1000,
        "churn_predictions": 250,
        "no_churn_predictions": 750,
        "churn_rate": 0.25,
        "average_churn_probability": 0.35
    }
    ```
    """
    batch_id: str
    total_records: int
    churn_predictions: int
    no_churn_predictions: int
    churn_rate: float
    average_churn_probability: float


class BatchJobResults(BaseModel):
    """
    Detailed results for a completed batch job.
    
    Contains individual predictions with original data.
    """
    batch_id: str
    total: int
    results: List[Dict[str, Any]]
    timestamp: str
    model_version: Optional[str] = None


# ============================================
# Feedback Schemas
# ============================================

class FeedbackRequest(BaseModel):
    """
    Request schema for submitting feedback on a prediction.
    
    Example Request:
    ```json
    {
        "actual_label": 0
    }
    ```
    """
    actual_label: int = Field(..., ge=0, le=1, description="Actual churn outcome: 0 = No churn, 1 = Churn", example=0)


class FeedbackResponse(BaseModel):
    """
    Response schema for feedback submission.
    
    Example Response:
    ```json
    {
        "status": "success",
        "prediction_id": "abc123-def456-ghi789",
        "actual_label": 0,
        "message": "Label recorded successfully"
    }
    ```
    """
    status: str
    prediction_id: str
    actual_label: int
    message: str


class BatchFeedbackRequest(BaseModel):
    """
    Request schema for batch feedback submission.
    
    Example Request:
    ```json
    {
        "feedbacks": [
            {"prediction_id": "id1", "actual_label": 0},
            {"prediction_id": "id2", "actual_label": 1}
        ]
    }
    ```
    """
    feedbacks: List[Dict[str, Any]] = Field(..., description="List of {prediction_id, actual_label}")


class BatchFeedbackResponse(BaseModel):
    """
    Response schema for batch feedback submission.
    """
    status: str
    total: int
    succeeded: int
    failed: int
    results: List[dict]


class CollectTrainingDataResponse(BaseModel):
    """
    Response schema for manual training data collection.
    """
    status: str
    message: str


# ============================================
# Model Management Schemas
# ============================================

class ModelMetadata(BaseModel):
    """
    Metadata for a model version in MLflow registry.
    
    Example Response:
    ```json
    {
        "name": "churn_model",
        "version": "3",
        "stage": "Production",
        "created_date": "2024-01-10T08:00:00Z",
        "last_updated": "2024-01-15T10:30:00Z",
        "metrics": {"accuracy": 0.85, "auc": 0.88}
    }
    ```
    """
    name: str
    version: str
    stage: str
    created_date: datetime
    last_updated: datetime
    metrics: Dict[str, float]


class ModelListResponse(BaseModel):
    """
    Response schema for current models listing.
    """
    production: Optional[ModelMetadata] = None
    staging: Optional[ModelMetadata] = None
    all_versions: List[ModelMetadata]


class ModelDeployRequest(BaseModel):
    """
    Request schema for deploying/promoting a model.
    
    Example Request:
    ```json
    {
        "model_name": "churn_model",
        "version": "4",
        "target_stage": "Production"
    }
    ```
    """
    model_name: str = Field(..., example="churn_model")
    version: str = Field(..., example="4")
    target_stage: str = Field(..., example="Production")


class ModelDeployResponse(BaseModel):
    """
    Response schema for model deployment.
    """
    success: bool
    model_name: str
    version: str
    target_stage: str
    message: str


class TriggerRetrainResponse(BaseModel):
    """
    Response schema for triggering retraining.
    
    Example Response:
    ```json
    {
        "status": "retraining_triggered",
        "task_id": "abc123-def456",
        "message": "Retraining task submitted"
    }
    ```
    """
    status: str
    task_id: str
    message: str


class RetrainTaskStatus(BaseModel):
    """
    Status of a retraining task.
    """
    task_id: str
    status: str
    ready: bool
    result: Optional[Dict] = None
    error: Optional[str] = None


class RetrainQueueStatus(BaseModel):
    """
    Status of the retrain queue.
    """
    queue_length: int
    max_batch_size: int
    status: str


# ============================================
# Drift Detection Schemas
# ============================================

class DriftCheckDetail(BaseModel):
    """
    Individual drift detection check result.
    """
    run_id: str
    timestamp: Any
    dataset_drift: bool


class DriftStatusResponse(BaseModel):
    """
    Response schema for drift monitoring status.
    """
    recent_checks: List[DriftCheckDetail]
    status: str


class DriftReportResponse(BaseModel):
    """
    Response schema for drift detection report.
    """
    has_drift: bool
    drifted_columns: List[str]
    timestamp: str
    report_url: str


class BatchDriftRequest(BaseModel):
    """
    Request schema for drift check on custom data.
    """
    data: List[PredictionRequest]


# ============================================
# Monitoring Schemas
# ============================================

class APIMetrics(BaseModel):
    """
    API performance metrics.
    """
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    average_response_time_ms: float
    requests_per_second: float


class SystemHealth(BaseModel):
    """
    System health status.
    """
    status: str
    timestamp: datetime
    mlflow_connected: bool
    postgres_connected: bool
    redis_connected: bool
    disk_usage_percent: float
    memory_usage_percent: float
    cpu_usage_percent: float


class HealthStatus(BaseModel):
    """
    Simple health check response.
    """
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]


class PredictionStats(BaseModel):
    """
    Aggregated prediction statistics.
    """
    total_predictions: int
    average_confidence: float
    churn_rate: float
    last_updated: str


# ============================================
# Error Schema
# ============================================

class ErrorResponse(BaseModel):
    """
    Standard error response format.
    """
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime