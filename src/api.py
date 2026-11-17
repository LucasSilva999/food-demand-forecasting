
from pathlib import Path

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ========================================
# MODEL CONFIGURATION
# ========================================

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "artifacts" / "demand_model.joblib"

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}. Run the training script first."
    )

model = joblib.load(MODEL_PATH)


# ========================================
# FASTAPI APPLICATION
# ========================================

app = FastAPI(
    title="Food Demand Prediction API",
    description="API for food demand forecasting using Machine Learning.",
    version="1.0.0"
)


# ========================================
# CORS CONFIGURATION
# ========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# INPUT VALIDATION
# ========================================

class PredictionInput(BaseModel):
    hour: int = Field(
        ge=0,
        le=23,
        description="Hour of the day"
    )

    weekday: int = Field(
        ge=0,
        le=6,
        description="Day of the week (Monday=0, Sunday=6)"
    )

    promotion: int = Field(
        ge=0,
        le=1,
        description="Promotion active: 0 or 1"
    )

    weather: str = Field(
        min_length=1,
        description="Weather condition"
    )

    zone: str = Field(
        min_length=1,
        description="Delivery zone"
    )


# ========================================
# ROUTES
# ========================================

@app.get("/")
def home():
    return {
        "message": "Food Demand Prediction API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }


@app.post("/predict")
def predict(data: PredictionInput):
    try:
        input_data = pd.DataFrame([data.model_dump()])

        prediction = float(model.predict(input_data)[0])

        return {
            "predicted_orders": round(max(0, prediction), 2),
            "unit": "orders"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {str(error)}"
        )
