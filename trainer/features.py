import pandas as pd

def prepare(df: pd.DataFrame, training=True, columns=None):
    df = df.copy()

    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])

    df["TotalCharges"] = pd.to_numeric(
        df["TotalCharges"],
        errors="coerce"
    )

    df = df.dropna()

    categorical = df.select_dtypes(include=["object"]).columns.tolist()

    if "Churn" in categorical:
        categorical.remove("Churn")

    df = pd.get_dummies(df, columns=categorical)

    if training:
        y = df["Churn"].map({"Yes": 1, "No": 0})
        X = df.drop(columns=["Churn"])

        return X, y, X.columns

    else:
        df = df.reindex(columns=columns, fill_value=0)
        return df