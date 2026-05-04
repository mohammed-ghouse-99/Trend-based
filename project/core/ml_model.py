"""
project/core/ml_model.py

ML Engine for TrendProject — Senior Level Version

Uses:
- Full technical indicator set from processor.py
- Boosted ensemble model (XGBoost for high performance)
- Consistent feature names across entire pipeline
- Stable training & prediction logic
"""

from typing import Tuple, List
import pandas as pd
import numpy as np
import os
import joblib

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# ------------------------------------------------------
# FIXED MODEL DIRECTORY
# ------------------------------------------------------
FILE_DIR = os.path.dirname(__file__)                 # project/core/
PROJECT_ROOT = os.path.abspath(os.path.join(FILE_DIR, ".."))  # project/
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")     # project/models
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "boosted_trend_model.pkl")


# ------------------------------------------------------
# FEATURE LIST — MUST MATCH processor.add_indicators()
# ------------------------------------------------------
FEATURES: List[str] = [
    # Moving Averages
    "SMA_10", "SMA_20", "SMA_50", "SMA_200",

    # EMAs
    "EMA_10", "EMA_20", "EMA_50",

    # Momentum indicators
    "RSI_14",
    "MOMENTUM_5", "MOMENTUM_10",

    # MACD
    "MACD", "MACD_SIGNAL", "MACD_HIST",

    # Volatility indicators
    "ATR_14", "VOL_20",

    # Regression slope
    "SLOPE_20",

    # Normalized price ratios
    "CLOSE_OVER_SMA50", "SMA50_OVER_SMA200",

    # Raw returns
    "RETURNS"
]


class TrendMLModel:
    def __init__(self, path: str = MODEL_PATH):
        self.model_path = path
        self.model = None

    # ------------------------------------------------------
    # PREPARE DATASET
    # ------------------------------------------------------
    def _build_dataset(self, df: pd.DataFrame, horizon: int = 1):
        df = df.copy()

        # Check required columns
        missing = [f for f in FEATURES if f not in df.columns]
        if missing:
            raise ValueError(f"Missing indicator columns: {missing}")

        # Target: tomorrow > today
        df["TARGET"] = (df["Close"].shift(-horizon) > df["Close"]).astype(int)

        df = df.dropna(subset=FEATURES + ["TARGET"])

        X = df[FEATURES].astype(float)
        y = df["TARGET"].astype(int)

        return X, y

    # ------------------------------------------------------
    # TRAIN MODEL (Boosted XGBoost)
    # ------------------------------------------------------
    def train(self, df: pd.DataFrame, test_size=0.2, horizon=1) -> Tuple[float, str]:
        X, y = self._build_dataset(df, horizon=horizon)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=True, random_state=42
        )

        # Senior-level boosted model
        model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.9,
            eval_metric="logloss"
        )

        model.fit(X_train, y_train)
        self.model = model

        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        report = classification_report(y_test, preds)

        # Save model
        joblib.dump(
            {"model": model, "features": FEATURES},
            self.model_path
        )

        return acc, report

    # ------------------------------------------------------
    # LOAD MODEL
    # ------------------------------------------------------
    def load(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        data = joblib.load(self.model_path)
        self.model = data["model"]
        return self.model

    # ------------------------------------------------------
    # PREDICT TREND
    # ------------------------------------------------------
    def predict(self, df: pd.DataFrame) -> Tuple[int, float]:
        if self.model is None:
            self.load()

        latest = df.tail(1)
        X = latest[FEATURES].astype(float)

        pred = int(self.model.predict(X)[0])
        conf = float(self.model.predict_proba(X)[0].max())

        return pred, conf
