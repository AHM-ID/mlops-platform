import sys
import pandas as pd
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, '/app')

from celery import Task
from worker.celery_app import app
from shared.retrain_queue import RetrainQueueManager
from shared.config import MLFLOW_TRACKING_URI, DATA_PATH
from shared.logging import setup_logging
from shared.metrics import DATASET_DRIFT, DRIFTED_COLUMNS_COUNT
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently import ColumnMapping
import mlflow

logger = setup_logging("drift_tasks")

class DriftTask(Task):
    _reference_data = None
    _column_mapping = None

    def get_reference_data(self):
        if self._reference_data is None:
            df = pd.read_csv(DATA_PATH)
            if "customerID" in df.columns:
                df = df.drop(columns=["customerID"])
            df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
            df = df.dropna()
            self._reference_data = df
            logger.info(f"Reference data loaded: {df.shape}")
        return self._reference_data

    def get_column_mapping(self):
        if self._column_mapping is None:
            self._column_mapping = ColumnMapping(
                target="Churn",
                numerical_features=["tenure", "MonthlyCharges", "TotalCharges"],
                categorical_features=["Contract", "InternetService", "PaymentMethod"]
            )
        return self._column_mapping

    def align_columns(self, current_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
        ref_cols = set(reference_df.columns)
        current_cols = set(current_df.columns)
        
        for col in ref_cols - current_cols:
            if col != "Churn":
                current_df[col] = 0
        
        for col in current_cols - ref_cols:
            if col != "Churn":
                current_df = current_df.drop(columns=[col])
        
        return_cols = [c for c in reference_df.columns if c != "Churn"]
        return current_df[return_cols]

@app.task(base=DriftTask, bind=True, name="periodic_drift_check")
def periodic_drift_check(self, hours_back: int = 24, min_samples: int = 100):
    logger.info(f"Starting periodic drift check (hours_back={hours_back}, min_samples={min_samples})")
    queue_manager = RetrainQueueManager()
    recent = queue_manager.get_recent_predictions(hours=hours_back)
    if len(recent) < min_samples:
        logger.warning(f"Insufficient samples for drift: {len(recent)} < {min_samples}")
        return {"status": "skipped", "reason": "insufficient_samples", "samples": len(recent)}
    records = []
    for rec in recent:
        if rec.get("features"):
            feat = rec["features"].copy()
            if rec.get("label") is not None:
                feat["Churn"] = "Yes" if rec["label"] == 1 else "No"
            records.append(feat)
    if not records:
        logger.warning("No valid feature records found")
        return {"status": "skipped", "reason": "no_features"}
    current_df = pd.DataFrame(records)
    reference_df = self.get_reference_data()
    current_df = self.align_columns(current_df, reference_df)
    column_mapping = self.get_column_mapping()
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference_df, current_data=current_df, column_mapping=column_mapping)
    report_dict = report.as_dict()
    dataset_drift = report_dict['metrics'][0]['result']['dataset_drift']
    drifted_columns = []
    for col_name, col_info in report_dict['metrics'][0]['result']['drift_by_columns'].items():
        if col_info.get('drift_detected', False):
            drifted_columns.append(col_name)
    DATASET_DRIFT.set(1 if dataset_drift else 0)
    DRIFTED_COLUMNS_COUNT.set(len(drifted_columns))
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    report_path = f"/tmp/drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report.save_html(report_path)
    with mlflow.start_run(run_name="auto_drift_check"):
        mlflow.log_param("hours_back", hours_back)
        mlflow.log_param("samples", len(recent))
        mlflow.log_metric("dataset_drift", int(dataset_drift))
        mlflow.log_metric("drifted_columns_count", len(drifted_columns))
        with open("drifted_columns.txt", "w") as f:
            f.write("\n".join(drifted_columns))
        mlflow.log_artifact("drifted_columns.txt")
        mlflow.log_artifact(report_path)
    if dataset_drift:
        logger.warning(
            "Data drift detected!",
            extra={
                "drifted_columns": drifted_columns,
                "samples": len(recent),
                "hours_back": hours_back,
                "task_id": self.request.id
            }
        )
    else:
        logger.info(f"No data drift detected (samples={len(recent)})")
    return {
        "status": "completed",
        "dataset_drift": dataset_drift,
        "drifted_columns": drifted_columns,
        "samples": len(recent),
        "timestamp": datetime.now().isoformat()
    }