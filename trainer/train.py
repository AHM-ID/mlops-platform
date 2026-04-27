import pandas as pd
import mlflow
import mlflow.sklearn
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from shared.config import *
from trainer.features import prepare
from trainer.optimize import search
from trainer.evaluate import metrics

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment(EXPERIMENT_NAME)

df = pd.read_csv("data/churn.csv")

X, y, cols = prepare(df, training=True)

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

best = search(X_train, y_train)

with mlflow.start_run():

    model = RandomForestClassifier(
        **best,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]

    scores = metrics(y_test, pred, prob)

    mlflow.log_params(best)
    mlflow.log_metrics(scores)

    joblib.dump(cols, "columns.pkl")
    mlflow.log_artifact("columns.pkl")

    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name=MODEL_NAME
    )