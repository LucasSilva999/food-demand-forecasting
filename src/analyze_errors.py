
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data" / "food_orders.csv"
ARTIFACTS = ROOT / "artifacts"

REPORTS = ROOT / "reports"
ANALYSIS = REPORTS / "analysis"
FIGURES = REPORTS / "figures"

PREDICTIONS_FILE = ARTIFACTS / "predictions.csv"


def main():
    if not DATA.exists():
        raise SystemExit("Dataset not found. Run the data generator first.")

    if not PREDICTIONS_FILE.exists():
        raise SystemExit(
            "Predictions not found. Run: py -m src.train"
        )

    # Load dataset and model predictions
    df = pd.read_csv(DATA, parse_dates=["timestamp"])
    predictions = pd.read_csv(
        PREDICTIONS_FILE,
        parse_dates=["timestamp"]
    )

    # Recover original information for each prediction
    analysis = predictions.merge(
        df,
        on="timestamp",
        how="left",
        suffixes=("", "_original")
    )

    # Positive error: model overpredicted.
    # Negative error: model underpredicted.
    analysis["signed_error"] = (
        analysis["predicted_orders"] - analysis["actual_orders"]
    )

    analysis["absolute_error"] = analysis["signed_error"].abs()

    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    # 1. Metrics by hour
    by_hour = (
        analysis.groupby("hour")
        .agg(
            samples=("actual_orders", "count"),
            mae=("absolute_error", "mean"),
            bias=("signed_error", "mean"),
            actual_mean=("actual_orders", "mean"),
            predicted_mean=("predicted_orders", "mean")
        )
        .reset_index()
        .round(3)
    )

    by_hour.to_csv(
        ANALYSIS / "errors_by_hour.csv",
        index=False
    )

    # 2. Metrics by zone
    by_zone = (
        analysis.groupby("zone")
        .agg(
            samples=("actual_orders", "count"),
            mae=("absolute_error", "mean"),
            bias=("signed_error", "mean"),
            actual_mean=("actual_orders", "mean"),
            predicted_mean=("predicted_orders", "mean")
        )
        .reset_index()
        .round(3)
    )

    by_zone.to_csv(
        ANALYSIS / "errors_by_zone.csv",
        index=False
    )

    # 3. Metrics by weekday
    by_weekday = (
        analysis.groupby("weekday")
        .agg(
            samples=("actual_orders", "count"),
            mae=("absolute_error", "mean"),
            bias=("signed_error", "mean")
        )
        .reset_index()
        .round(3)
    )

    by_weekday.to_csv(
        ANALYSIS / "errors_by_weekday.csv",
        index=False
    )

    # 4. MAE by hour
    plt.figure(figsize=(10, 5))
    plt.bar(by_hour["hour"], by_hour["mae"])
    plt.title("MAE by hour")
    plt.xlabel("Hour of day")
    plt.ylabel("Mean absolute error (orders)")
    plt.xticks(range(24))
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        FIGURES / "mae_by_hour.png",
        dpi=150
    )
    plt.close()

    # 5. Prediction bias by hour
    plt.figure(figsize=(10, 5))
    plt.bar(by_hour["hour"], by_hour["bias"])
    plt.axhline(0, linestyle="--")
    plt.title("Prediction bias by hour")
    plt.xlabel("Hour of day")
    plt.ylabel("Mean error (predicted - actual)")
    plt.xticks(range(24))
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        FIGURES / "bias_by_hour.png",
        dpi=150
    )
    plt.close()

    # 6. Actual vs predicted orders
    ordered = analysis.sort_values("timestamp")

    plt.figure(figsize=(13, 5))
    plt.plot(
        ordered["timestamp"],
        ordered["actual_orders"],
        label="Actual orders"
    )
    plt.plot(
        ordered["timestamp"],
        ordered["predicted_orders"],
        label="Predicted orders"
    )
    plt.title("Actual vs predicted orders")
    plt.xlabel("Date")
    plt.ylabel("Number of orders")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        FIGURES / "actual_vs_predicted.png",
        dpi=150
    )
    plt.close()

    # 7. Overall summary
    overall_mae = analysis["absolute_error"].mean()
    overall_bias = analysis["signed_error"].mean()

    worst_hour = by_hour.loc[by_hour["mae"].idxmax()]
    best_hour = by_hour.loc[by_hour["mae"].idxmin()]

    print("\n========== ERROR ANALYSIS ==========")
    print(f"Overall MAE: {overall_mae:.3f}")
    print(f"Overall bias: {overall_bias:.3f}")

    print(
        f"\nWorst hour: {int(worst_hour['hour'])}h "
        f"(MAE: {worst_hour['mae']:.3f})"
    )

    print(
        f"Best hour: {int(best_hour['hour'])}h "
        f"(MAE: {best_hour['mae']:.3f})"
    )

    print("\nErrors by hour:")
    print(by_hour.to_string(index=False))

    print("\nErrors by zone:")
    print(by_zone.to_string(index=False))

    print("\nGenerated files:")
    print("- reports/analysis/errors_by_hour.csv")
    print("- reports/analysis/errors_by_zone.csv")
    print("- reports/analysis/errors_by_weekday.csv")
    print("- reports/figures/mae_by_hour.png")
    print("- reports/figures/bias_by_hour.png")
    print("- reports/figures/actual_vs_predicted.png")


if __name__ == "__main__":
    main()
