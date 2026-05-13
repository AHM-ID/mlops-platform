import pandas as pd
from typing import Optional, Tuple, Union, List


def _drop_customer_id(df: pd.DataFrame) -> pd.DataFrame:
    if "customerID" in df.columns:
        return df.drop(columns=["customerID"])
    return df


def _coerce_total_charges(df: pd.DataFrame) -> pd.DataFrame:
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    return df


def _get_categorical_columns(df: pd.DataFrame) -> List[str]:
    categorical = df.select_dtypes(include=["object"]).columns.tolist()
    if "Churn" in categorical:
        categorical.remove("Churn")
    return categorical


def _encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    categorical = _get_categorical_columns(df)
    return pd.get_dummies(df, columns=categorical)


def _split_target(df: pd.DataFrame):
    y = df["Churn"].map({"Yes": 1, "No": 0})
    X = df.drop(columns=["Churn"])
    return X, y, X.columns


def _align_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = 0
    return df[columns]


def prepare(
    df: pd.DataFrame, 
    training: bool = True, 
    columns: Optional[List[str]] = None
):
    df = df.copy()
    df = _drop_customer_id(df)
    df = _coerce_total_charges(df)
    df = df.dropna()
    df = _encode_categoricals(df)
    
    if training:
        return _split_target(df)
    else:
        return df.reindex(columns=columns, fill_value=0)