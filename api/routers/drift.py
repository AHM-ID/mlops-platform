from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
import pandas as pd
import mlflow
from datetime import datetime
from pydantic import BaseModel
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently import ColumnMapping
from shared.config import DATA_PATH, MLFLOW_TRACKING_URI
from shared.logging import setup_logging
from api.auth import require_read, require_write
from api.schemas import DriftStatusResponse, PredictionRequest, TriggerRetrainResponse
from worker.celery_app import app as celery_app
from worker.drift_tasks import periodic_drift_check

logger = setup_logging("drift_router")
router = APIRouter()

class DriftReportResponse(BaseModel):
    has_drift: bool
    drifted_columns: List[str]
    timestamp: str
    report_url: str

class BatchDriftRequest(BaseModel):
    data: List[PredictionRequest]

def get_reference_data():
    df = pd.read_csv(DATA_PATH)
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df = df.dropna()
    return df

def get_column_mapping():
    return ColumnMapping(
        target="Churn",
        numerical_features=["tenure", "MonthlyCharges", "TotalCharges"],
        categorical_features=["Contract", "InternetService", "PaymentMethod"]
    )

def run_drift_report(current_data: pd.DataFrame, reference_data: pd.DataFrame) -> Dict[str, Any]:
    column_mapping = get_column_mapping()
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
    "/drift/check",
    response_model=DriftReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Check data drift for current batch"
)
async def check_data_drift(
    request: BatchDriftRequest,
    role: str = Depends(require_read)
):
    try:
        logger.info(f"Data drift check requested by role {role}, records={len(request.data)}")
        current_df = pd.DataFrame([{
            "tenure": r.tenure,
            "MonthlyCharges": r.MonthlyCharges,
            "TotalCharges": r.TotalCharges,
            "Contract": r.Contract,
            "InternetService": r.InternetService,
            "PaymentMethod": r.PaymentMethod
        } for r in request.data])
        reference_df = get_reference_data()
        result = run_drift_report(current_df, reference_df)
        return DriftReportResponse(
            has_drift=result["has_drift"],
            drifted_columns=result["drifted_columns"],
            timestamp=datetime.now().isoformat(),
            report_url=result["report_path"]
        )
    except Exception as e:
        logger.error(f"Data drift check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data drift check failed: {str(e)}"
        )

@router.post(
    "/drift/auto-check",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger automatic drift check from Redis"
)
async def trigger_auto_drift_check(role: str = Depends(require_read)):
    """Trigger drift detection using stored predictions from Redis"""
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
            detail=f"Failed to trigger drift check: {str(e)}"
        )

@router.get(
    "/drift/status",
    response_model=DriftStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recent drift detection status"
)
async def get_drift_status(role: str = Depends(require_read)) -> DriftStatusResponse:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        experiments = mlflow.search_experiments()
        drift_metrics = []
        for exp in experiments:
            runs = mlflow.search_runs(experiment_ids=[exp.experiment_id], filter_string="tags.mlflow.runName = 'data_drift_check'")
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
    except Exception as e:
        logger.error(f"Failed to get drift status: {e}")
        return DriftStatusResponse(recent_checks=[], status="error")

@router.post(
    "/drift/trigger_retrain",
    response_model=TriggerRetrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger retraining if drift detected"
)
async def trigger_retrain_on_drift(
    role: str = Depends(require_write)
) -> TriggerRetrainResponse:
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
            detail=f"Failed to trigger retraining: {str(e)}"
        )