
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.dummy import DummyRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV

from src.features import FEATURES, TARGET, build_model


ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data" / "food_orders.csv"
ARTIFACTS = ROOT / "artifacts"

BASE_MODELS = [
    "random_forest",
    "linear_regression",
    "gradient_boosting"
]


def calculate_metrics(y_true, y_pred):
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "r2": round(float(r2_score(y_true, y_pred)), 3)
    }


def main():
    if not DATA.exists():
        raise SystemExit(
            "Dataset not found. Run: py -m src.generate_data"
        )

    df = pd.read_csv(DATA, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    split = int(len(df) * 0.8)

    train = df.iloc[:split]
    test = df.iloc[split:]

    X_train = train[FEATURES]
    y_train = train[TARGET]

    X_test = test[FEATURES]
    y_test = test[TARGET]

    time_split = TimeSeriesSplit(n_splits=3)

    # Baseline
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(X_train, y_train)

    baseline_metrics = calculate_metrics(
        y_test,
        baseline.predict(X_test)
    )

    results = {}
    fitted_models = {}

    # Comparação dos modelos anteriores
    for model_name in BASE_MODELS:
        print(f"\nEvaluating: {model_name}")

        model = build_model(model_name)

        cv_scores = cross_val_score(
            model,
            X_train,
            y_train,
            cv=time_split,
            scoring="neg_mean_absolute_error",
            n_jobs=1
        )

        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        results[model_name] = {
            "cv_mae_mean": round(float((-cv_scores).mean()), 3),
            "cv_mae_std": round(float(cv_scores.std()), 3),
            "test_metrics": calculate_metrics(y_test, predictions)
        }

        fitted_models[model_name] = model

    # Busca de hiperparâmetros do Gradient Boosting
    print("\nStarting Gradient Boosting hyperparameter tuning...")

    param_grid = {
        "model__n_estimators": [100, 200, 300],
        "model__learning_rate": [0.03, 0.05, 0.08],
        "model__max_depth": [2, 3],
        "model__min_samples_leaf": [2, 4]
    }

    search = GridSearchCV(
        estimator=build_model("gradient_boosting"),
        param_grid=param_grid,
        scoring="neg_mean_absolute_error",
        cv=time_split,
        n_jobs=-1,
        refit=True,
        verbose=1
    )

    search.fit(X_train, y_train)

    tuned_model = search.best_estimator_
    tuned_predictions = tuned_model.predict(X_test)

    results["tuned_gradient_boosting"] = {
        "cv_mae_mean": round(float(-search.best_score_), 3),
        "cv_mae_std": round(
            float(search.cv_results_["std_test_score"][search.best_index_]),
            3
        ),
        "test_metrics": calculate_metrics(
            y_test,
            tuned_predictions
        ),
        "best_parameters": search.best_params_
    }

    fitted_models["tuned_gradient_boosting"] = tuned_model

    # Escolhe o modelo pela validação temporal
    best_model_name = min(
        results,
        key=lambda name: results[name]["cv_mae_mean"]
    )

    best_model = fitted_models[best_model_name]
    best_predictions = best_model.predict(X_test)

    best_metrics = calculate_metrics(y_test, best_predictions)

    improvement = (
        (baseline_metrics["mae"] - best_metrics["mae"])
        / baseline_metrics["mae"]
        * 100
    )

    # Salva previsões
    prediction_report = pd.DataFrame({
        "timestamp": test["timestamp"].values,
        "actual_orders": y_test.values,
        "predicted_orders": best_predictions.round(2),
        "absolute_error": np.abs(
            y_test.values - best_predictions
        ).round(2)
    })

    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    prediction_report.to_csv(
        ARTIFACTS / "predictions.csv",
        index=False
    )

    # Salva o melhor modelo
    joblib.dump(
        best_model,
        ARTIFACTS / "demand_model.joblib"
    )

    # Relatório final
    report = {
        "baseline": baseline_metrics,
        "models": results,
        "best_model": best_model_name,
        "best_model_test_metrics": best_metrics,
        "mae_improvement_vs_baseline_percent": round(
            float(improvement), 2
        ),
        "split": {
            "train_rows": len(train),
            "test_rows": len(test),
            "strategy": "chronological 80/20"
        },
        "cross_validation": {
            "strategy": "TimeSeriesSplit",
            "folds": 3
        },
        "hyperparameter_tuning": {
            "method": "GridSearchCV",
            "combinations": 36,
            "selection_metric": "negative MAE"
        },
        "feature_engineering": [
            "cyclical_hour",
            "cyclical_weekday",
            "promotion_hour_interaction",
            "hour_period",
            "hour_zone_interaction"
        ],
        "data": "synthetic; seed=42"
    }

    (ARTIFACTS / "metrics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n========== FINAL RESULTS ==========")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    print("\nSaved files:")
    print("- artifacts/demand_model.joblib")
    print("- artifacts/metrics.json")
    print("- artifacts/predictions.csv")


if __name__ == "__main__":
    main()
