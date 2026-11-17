
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.linear_model import LinearRegression


# Entradas originais
FEATURES = [
    "hour",
    "weekday",
    "promotion",
    "weather",
    "zone"
]

TARGET = "orders"

# Atributos numéricos após engenharia de atributos
NUMERIC_FEATURES = [
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "promotion",
    "promotion_hour_sin",
    "promotion_hour_cos"
]

# Atributos categóricos após engenharia de atributos
CATEGORICAL_FEATURES = [
    "weather",
    "zone",
    "hour_period",
    "hour_zone"
]


def add_engineered_features(df):
    df = df.copy()

    # Representação cíclica do horário
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Representação cíclica do dia da semana
    df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
    df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)

    # Interação entre promoção e horário
    df["promotion_hour_sin"] = (
        df["promotion"] * df["hour_sin"]
    )

    df["promotion_hour_cos"] = (
        df["promotion"] * df["hour_cos"]
    )

    # Períodos do dia
    df["hour_period"] = np.select(
        [
            df["hour"] < 6,
            df["hour"] < 11,
            df["hour"] < 15,
            df["hour"] < 18
        ],
        [
            "night",
            "morning",
            "lunch",
            "afternoon"
        ],
        default="evening"
    )

    # Interação entre período do dia e zona
    df["hour_zone"] = (
        df["hour_period"].astype(str)
        + "_"
        + df["zone"].astype(str)
    )

    # Remove as colunas originais já transformadas
    df = df.drop(columns=["hour", "weekday"])

    return df


def build_model(model_name="gradient_boosting"):
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median"))
    ])

    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore"))
    ])

    preprocess = ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES)
    ])

    if model_name == "random_forest":
        estimator = RandomForestRegressor(
            n_estimators=250,
            max_depth=14,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )

    elif model_name == "gradient_boosting":
        estimator = GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=3,
            min_samples_leaf=2,
            random_state=42
        )

    elif model_name == "linear_regression":
        estimator = LinearRegression()

    else:
        raise ValueError(f"Unknown model: {model_name}")

    return Pipeline([
        (
            "feature_engineering",
            FunctionTransformer(
                add_engineered_features,
                validate=False
            )
        ),
        ("preprocess", preprocess),
        ("model", estimator)
    ])
