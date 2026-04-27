import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

def search(X, y):
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 200),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 8),
            "random_state": 42,
            "n_jobs": -1
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

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42)
    )

    study.optimize(objective, n_trials=15)

    return study.best_params