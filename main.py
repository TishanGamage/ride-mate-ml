from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import joblib
import pandas as pd
import os

# ── Load model on startup ─────────────────────────────
MODEL_PATH   = "model/acceptance_model_v2.pkl"
FEATURES     = ["route_deviation_pct", "zone_density",
                "trip_distance_km", "heading_angle_deg"]
MODEL_VERSION = "gradient_boosting_v2"

try:
    model =  joblib.load(MODEL_PATH)
    model_loaded = True
except Exception as e:
    model_loaded = False
    print(f"Model load failed: {e}")

app = FastAPI(title="Driver Acceptance Rate Predictor")

# ── Request / Response schemas ────────────────────────
class DriverInput(BaseModel):
    driver_id: str
    route_deviation_pct: float
    zone_density: int
    trip_distance_km: float
    heading_angle_deg: float

class PredictRequest(BaseModel):
    passenger_id: Optional[str] = None
    drivers: List[DriverInput]

class RankedDriver(BaseModel):
    rank: int
    driver_id: str
    predicted_acceptance_rate: float
    route_deviation_pct: float
    zone_density: int
    trip_distance_km: float
    heading_angle_deg: float

class PredictResponse(BaseModel):
    passenger_id: Optional[str]
    ranked_drivers: List[RankedDriver]
    top_driver_id: str
    model_version: str

# ── Endpoints ─────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "model_version": MODEL_VERSION
    }

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if not model_loaded:
        raise HTTPException(status_code=503,
                            detail="Model not loaded")
    if len(request.drivers) == 0:
        raise HTTPException(status_code=400,
                            detail="No drivers provided")

    # Build input dataframe
    df = pd.DataFrame([{
        "route_deviation_pct": d.route_deviation_pct,
        "zone_density":        d.zone_density,
        "trip_distance_km":    d.trip_distance_km,
        "heading_angle_deg":   d.heading_angle_deg,
    } for d in request.drivers])

    # Predict
    scores = model.predict(df[FEATURES])

    # Attach scores and rank
    results = []
    for i, driver in enumerate(request.drivers):
        results.append({
            "driver":  driver,
            "score":   round(float(scores[i]), 4)
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    ranked = [
        RankedDriver(
            rank=i + 1,
            driver_id=r["driver"].driver_id,
            predicted_acceptance_rate=r["score"],
            route_deviation_pct=r["driver"].route_deviation_pct,
            zone_density=r["driver"].zone_density,
            trip_distance_km=r["driver"].trip_distance_km,
            heading_angle_deg=r["driver"].heading_angle_deg,
        )
        for i, r in enumerate(results)
    ]

    return PredictResponse(
        passenger_id=request.passenger_id,
        ranked_drivers=ranked,
        top_driver_id=ranked[0].driver_id,
        model_version=MODEL_VERSION
    )