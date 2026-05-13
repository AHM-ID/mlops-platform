import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

SEARCH_SPACE = {
    "n_estimators": (50, 200),
    "max_depth": (3, 10),
    "min_samples_split": (2, 8),
}

FIXED_PARAMS = {
    "random_state": 42,
    "n_jobs": -1,
}

def _create_objective(X, y):
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", *SEARCH_SPACE["n_estimators"]),
            "max_depth": trial.suggest_int("max_depth", *SEARCH_SPACE["max_depth"]),
            "min_samples_split": trial.suggest_int("min_samples_split", *SEARCH_SPACE["min_samples_split"]),
            **FIXED_PARAMS
        }

        model = RandomForestClassifier(**params)

        score = cross_val_score(
            model,
            X,
            y,
            cv=5,
            scoring="roc_auc",
            n_jobs=-1
        ).mean()

        return score
    
    return objective

def search(X, y):
    objective = _create_objective(X, y)
    
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42)
    )

    study.optimize(objective, n_trials=15)

    return study.best_params
