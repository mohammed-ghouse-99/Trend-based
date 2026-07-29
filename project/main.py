"""
project/main.py

Training script for TrendProject
--------------------------------
Pipeline:
1) Fetch OHLCV (+ Adj Close) data from Yahoo via get_data()
2) Add full technical indicators via project.data.processor.add_indicators()
3) Build a supervised dataset: target = (tomorrow_close > today_close)
4) Train RandomForestClassifier on rich feature set
5) Save model + feature list to project/models/model.pkl

This model is then used by:
- Streamlit dashboard (dashboard.py)
- ML prediction block (joblib.load + ['model']['features'])
"""

import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pickle

#  Correct imports (project is a package)
from project.data.collector import get_data
from project.data.processor import add_indicators


# =========================================
# 1) Target creation helper
# -----------------------------------------
# Target_t = 1 if Close[t+1] > Close[t] else 0
# =========================================
def add_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    return df.dropna(subset=["Target"])


# =========================================
# 2) MAIN TRAINING FUNCTION
# =========================================
def train_model(ticker: str = "AAPL") -> None:
    print(f"\n Fetching data for: {ticker}")

    # ---- STEP 1: Get OHLCV + Adj Close from collector.py ----
    df = get_data(ticker=ticker, period="3y", interval="1d")

    if df is None or df.empty:
        print(" Error: No data fetched. Check ticker or internet.")
        return

    print(f" Retrieved {len(df)} rows of raw OHLCV data")

    # ---- STEP 2: Add ALL technical indicators (processor.py) ----
    print(" Adding indicators...")
    df_ind = add_indicators(df, dropna=True)
    print(f" Indicators added. Final rows: {len(df_ind)}")
    # At this stage df_ind has:
    # OHLCV + Adj Close (from collector) + SMA/EMA/RSI/MACD/ATR/etc

    # ---- STEP 3: Add Target (label) ----
    df_ind = add_target(df_ind)
    print(f" Target column added. Rows after target dropna: {len(df_ind)}")

    # ---- STEP 4: Define feature set (rich, ML-focused) ----
    # These names MUST match columns created in processor.py
    FEATURE_COLS = [
        # core price/volume
        "Open", "High", "Low", "Close", "Volume", "Adj Close",

        # trend indicators
        "SMA_10", "SMA_20", "SMA_50", "SMA_200",
        "EMA_10", "EMA_20", "EMA_50",

        # oscillator / momentum
        "RSI_14",
        "MOMENTUM_5", "MOMENTUM_10",

        # volatility + ATR
        "ATR_14", "RETURNS", "VOL_20",

        # MACD family
        "MACD", "MACD_SIGNAL", "MACD_HIST",

        # regression slope + normalized ratios
        "SLOPE_20",
        "CLOSE_OVER_SMA50", "SMA50_OVER_SMA200",
    ]

    # safety check: make sure all these columns exist
    missing = [c for c in FEATURE_COLS if c not in df_ind.columns]
    if missing:
        print(f" Missing required feature columns: {missing}")
        print("   Available columns:", list(df_ind.columns))
        return

    X = df_ind[FEATURE_COLS].astype(float)
    y = df_ind["Target"].astype(int)

    print(f"\n Dataset shape → X: {X.shape}, y: {y.shape}")
    print(f"   Class balance (0=DOWN, 1=UP):")
    print(y.value_counts(normalize=True).rename("proportion"))

    # ---- STEP 5: Train/Test split ----
    # shuffle=True → random split for ML learning
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        shuffle=True,
        stratify=y  # preserve class ratio
    )

    # ---- STEP 6: Train RandomForest ----
    print("\n Training RandomForest model...")
    model = RandomForestClassifier(
        n_estimators=300,   # more trees → more stable
        max_depth=10,      # deeper trees → capture non-linear trends
        random_state=42,
        n_jobs=-1          # use all CPU cores
    )
    model.fit(X_train, y_train)

    # ---- STEP 7: Evaluate ----
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"\n Model Accuracy: {acc:.4f}")

    print("\n Classification Report:")
    print(classification_report(y_test, preds, digits=4))

    # ---- STEP 8: Save model + feature list ----
    payload = {
        "model": model,
        "features": FEATURE_COLS
    }

    os.makedirs("project/models", exist_ok=True)
    model_path = "project/models/model.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(payload, f)

    print(f"\n Model saved to: {model_path}")
    print(" TRAINING COMPLETE")


# =========================================
# 3) ENTRY POINT
# =========================================
if __name__ == "__main__":
    train_model("AAPL")
