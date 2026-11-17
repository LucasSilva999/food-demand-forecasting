import argparse
import joblib
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Predict hourly food-order demand.")
    parser.add_argument("--hour", type=int, required=True, choices=range(24))
    parser.add_argument("--weekday", type=int, required=True, choices=range(7), help="Monday=0 ... Sunday=6")
    parser.add_argument("--promotion", type=int, choices=[0, 1], default=0)
    parser.add_argument("--weather", choices=["clear", "cloudy", "rain"], default="clear")
    parser.add_argument("--zone", choices=["central", "north", "south"], default="central")
    args = parser.parse_args()
    try:
        model = joblib.load("artifacts/demand_model.joblib")
    except FileNotFoundError:
        raise SystemExit("Model not found. Run: python -m src.generate_data && python -m src.train")
    sample = pd.DataFrame([vars(args)])
    prediction = max(0, float(model.predict(sample)[0]))
    print(f"Estimated orders: {prediction:.1f}")

if __name__ == "__main__":
    main()
