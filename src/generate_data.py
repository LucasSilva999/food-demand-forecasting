from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
OUTPUT = Path("data/food_orders.csv")

def make_dataset(rows: int = 2400, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=rows, freq="h")
    hour = dates.hour
    weekday = dates.day_of_week
    promotion = rng.binomial(1, 0.22, rows)
    weather = rng.choice(["clear", "cloudy", "rain"], rows, p=[0.50, 0.30, 0.20])
    zone = rng.choice(["central", "north", "south"], rows)
    zone_effect = pd.Series(zone).map({"central": 18, "north": 8, "south": 3}).to_numpy()
    meal_peak = 24 * np.exp(-((hour - 12) / 2.8) ** 2) + 34 * np.exp(-((hour - 19) / 3.0) ** 2)
    weekend = np.where(weekday >= 5, 12, 0)
    promo_effect = promotion * 16
    weather_effect = np.select([weather == "rain", weather == "cloudy"], [-7, -2], default=0)
    trend = np.linspace(0, 5, rows)
    noise = rng.normal(0, 7, rows)
    orders = np.maximum(0, 12 + meal_peak + weekend + promo_effect + zone_effect + weather_effect + trend + noise)
    return pd.DataFrame({
        "timestamp": dates,
        "hour": hour,
        "weekday": weekday,
        "promotion": promotion,
        "weather": weather,
        "zone": zone,
        "orders": np.round(orders).astype(int),
    })

def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df = make_dataset()
    df.to_csv(OUTPUT, index=False)
    print(f"Saved {len(df)} synthetic rows to {OUTPUT}")

if __name__ == "__main__":
    main()
