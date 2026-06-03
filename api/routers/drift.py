"""
Drift Detection Router - Standalone

Endpoints:
- POST   /drift/check      - Trigger immediate drift check
- POST   /drift/auto-check - Trigger auto drift check (async)
- GET    /drift/status     - Get drift detection status
- POST   /drift/retrain    - Trigger retraining on drift
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.concurrency import run_in_threadpool
from typing import List
import pandas as pd
import mlflow
from datetime import datetime
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently import ColumnMapping

from shared.config import DATA_PATH, MLFLOW_TRACKING_URI
from shared.logging import setup_logging
from api.auth import require_read, require_write
from api.schemas import (
    DriftStatusResponse, DriftReportResponse, 
    BatchDriftRequest, PredictionRequest, TriggerRetrainResponse
)
from worker.celery_app import app as celery_app
from worker.drift_tasks import periodic_drift_check

logger = setup_logging("drift_router")
router = APIRouter(tags=["Drift Detection"])


def get_reference_data():
    """Load reference data from CSV for drift comparison"""
    df = pd.read_csv(DATA_PATH)
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df = df.dropna()
    return df


def get_column_mapping():
    """Get column mapping for Evidently drift detection"""
    return ColumnMapping(
        target=None,
        numerical_features=["tenure", "MonthlyCharges", "TotalCharges"],
        categorical_features=[
            "Contract", "InternetService", "PaymentMethod", 
            "gender", "Partner", "Dependents", "PhoneService",
            "MultipleLines", "OnlineSecurity", "OnlineBackup",
            "DeviceProtection", "TechSupport", "StreamingTV", 
            "StreamingMovies", "PaperlessBilling"
        ]
    )


def preprocess_current_data(data: List[PredictionRequest]) -> pd.DataFrame:
    """Convert prediction requests to DataFrame for drift analysis"""
    records = []
    for r in data:
        record = {
            "gender": r.gender,
            "SeniorCitizen": r.SeniorCitizen,
            "Partner": r.Partner,
            "Dependents": r.Dependents,
            "tenure": r.tenure,
            "PhoneService": r.PhoneService,
            "MultipleLines": r.MultipleLines,
            "InternetService": r.InternetService,
            "OnlineSecurity": r.OnlineSecurity,
            "OnlineBackup": r.OnlineBackup,
            "DeviceProtection": r.DeviceProtection,
            "TechSupport": r.TechSupport,
            "StreamingTV": r.StreamingTV,
            "StreamingMovies": r.StreamingMovies,
            "Contract": r.Contract,
            "PaperlessBilling": r.PaperlessBilling,
            "PaymentMethod": r.PaymentMethod,
            "MonthlyCharges": r.MonthlyCharges,
            "TotalCharges": r.TotalCharges,
        }
        records.append(record)
    return pd.DataFrame(records)


def align_columns(current_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    """Align columns between current and reference dataframes"""
    ref_cols = set(reference_df.columns)
    current_cols = set(current_df.columns)
    cols_to_keep = [c for c in current_cols if c in ref_cols and c != "Churn"]
    return current_df[cols_to_keep]


def run_drift_report(current_data: pd.DataFrame, reference_data: pd.DataFrame) -> dict:
    """Execute drift detection report"""
    column_mapping = get_column_mapping()
    current_data = align_columns(current_data, reference_data)
    
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)
    
    report_dict = report.as_dict()
    dataset_drift = report_dict['metrics'][0]['result']['dataset_drift']
    
    drifted_columns = []
    if 'metrics' in report_dict and len(report_dict['metrics']) > 0:
        if 'result' in report_dict['metrics'][0] and 'drift_by_columns' in report_dict['metrics'][0]['result']:
            for col_name, col_info in report_dict['metrics'][0]['result']['drift_by_columns'].items():
                if col_info.get('drift_detected', False):
                    drifted_columns.append(col_name)
    
    report_path = f"/tmp/drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report.save_html(report_path)
    
    # Log to MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    try:
        with mlflow.start_run(run_name="data_drift_check"):
            mlflow.log_metric("dataset_drift", int(dataset_drift))
            mlflow.log_artifact(report_path)
    except Exception as e:
        logger.warning(f"Failed to log drift report to MLflow: {e}")
    
    return {
        "has_drift": dataset_drift,
        "drifted_columns": drifted_columns,
        "report_path": report_path
    }


@router.post(
    "/check",
    response_model=DriftReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Data Drift",
    description="Check for data drift by comparing current data with reference data."
)
async def check_data_drift(
    request: BatchDriftRequest,
    role: str = Depends(require_read)
) -> DriftReportResponse:
    """
    Check for data drift.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/drift/check" \\
         -H "X-API-Key: user-secret-key-change-in-production" \\
         -H "Content-Type: application/json" \\
         -d '{"data": [<PredictionRequest objects>]}'
    ```
    """
    logger.info(f"Drift check requested, records={len(request.data)}")
    
    current_df = preprocess_current_data(request.data)
    reference_df = await run_in_threadpool(get_reference_data)
    result = await run_in_threadpool(run_drift_report, current_df, reference_df)
    
    return DriftReportResponse(
        has_drift=result["has_drift"],
        drifted_columns=result["drifted_columns"],
        timestamp=datetime.now().isoformat(),
        report_url=result["report_path"]
    )


@router.post(
    "/auto-check",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Auto Drift Check",
    description="Trigger an asynchronous drift check using recent predictions from Redis."
)
async def trigger_auto_drift_check(role: str = Depends(require_read)):
    """
    Trigger automatic drift check (async).
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/drift/auto-check" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    try:
        task = periodic_drift_check.delay(24, 100)
        logger.info(f"Auto drift check triggered, task_id={task.id}")
        return {
            "task_id": task.id,
            "status": "started",
            "message": "Drift check will use recent predictions from Redis"
        }
    except Exception as e:
        logger.error(f"Failed to trigger auto drift check: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to trigger drift check. Service temporarily unavailable."
        )


@router.get(
    "/status",
    response_model=DriftStatusResponse,
    summary="Get Drift Status",
    description="Get recent drift detection results and monitoring status."
)
async def get_drift_status(role: str = Depends(require_read)) -> DriftStatusResponse:
    """
    Get drift detection status.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/drift/status" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        experiment = mlflow.get_experiment_by_name("customer_churn")
        
        if experiment:
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id], 
                filter_string="tags.mlflow.runName = 'data_drift_check'"
            )
            drift_metrics = []
            for _, run in runs.iterrows():
                if 'metrics.dataset_drift' in run:
                    drift_metrics.append({
                        "run_id": run.run_id,
                        "timestamp": run.start_time,
                        "dataset_drift": bool(run['metrics.dataset_drift'])
                    })
            return DriftStatusResponse(
                recent_checks=drift_metrics[-10:],
                status="monitoring_active"
            )
        
        return DriftStatusResponse(recent_checks=[], status="monitoring_active")
    
    except Exception as e:
        logger.error(f"Failed to get drift status: {e}")
        return DriftStatusResponse(recent_checks=[], status="error")


@router.post(
    "/retrain",
    response_model=TriggerRetrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Retraining on Drift",
    description="Trigger model retraining when data drift is detected."
)
async def trigger_retrain_on_drift(role: str = Depends(require_write)) -> TriggerRetrainResponse:
    """
    Trigger retraining based on drift detection.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/drift/retrain" \\
         -H "X-API-Key: admin-secret-key-change-in-production"
    ```
    """
    try:
        from worker.celery_app import retrain
        task = retrain.delay()
        logger.info(f"Retraining triggered by drift detection, task_id={task.id}")
        return TriggerRetrainResponse(
            status="retraining_triggered",
            task_id=task.id,
            message="Retraining task submitted due to data drift detection"
        )
    except Exception as e:
        logger.error(f"Failed to trigger retrain: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to trigger retraining. Service temporarily unavailable."
        )