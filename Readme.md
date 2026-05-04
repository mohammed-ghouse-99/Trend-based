# TrendProject — AI Trend Detection & ML Stock Predictor

TrendProject is a **quantitative trading analytics dashboard** that combines **market structure analysis, technical indicators, machine learning, Renko trend detection, and time-series forecasting** to analyze financial markets.

The project provides a **real-time interactive Streamlit dashboard** capable of:

* Detecting market trends using pure price structure
* Predicting next-day price direction using machine learning
* Filtering market noise using Renko charts
* Summarizing indicator signals into trading bias
* Forecasting future price movement using Prophet

The system integrates **data engineering, quantitative analysis, machine learning, and visualization** into a unified architecture.

---

# Table of Contents

1. Project Overview
2. System Architecture
3. Core Features
4. Data Pipeline
5. Technical Indicators Engine
6. Market Structure Trend Detection
7. Machine Learning Model
8. Renko Trend Detection
9. Prophet Forecasting Engine
10. Technical Summary System
11. Visualization Layer
12. Caching System
13. Model Training Pipeline
14. Dashboard Features
15. Project Structure
16. Installation
17. Usage
18. Future Improvements

---

# Project Overview

TrendProject aims to replicate the **analysis workflow used by professional trading platforms** such as:

* TradingView
* Investing.com
* Bloomberg Terminal (simplified)

The system integrates **three independent analysis engines**:

1. **Market Structure Trend Detector**
2. **Machine Learning Predictor**
3. **Renko Trend Analyzer**

These engines provide **independent insights** about market behavior.

---

# System Architecture

TrendProject follows a **modular architecture**.

```
Data Layer
   ↓
Indicator Engine
   ↓
Analysis Engines
   ├── Trend Detector
   ├── ML Predictor
   ├── Renko Engine
   └── Prophet Forecast
   ↓
Signal Aggregation
   ↓
Visualization Dashboard
```

The project separates responsibilities into dedicated modules:

```
project/
│
├── core/
│   ├── trend_detector.py
│   ├── renko.py
│   ├── ml_model.py
│   ├── prophet_model.py
│   └── utils.py
│
├── data/
│   ├── collector.py
│   ├── processor.py
│   └── storage.py
│
├── visual/
│   └── charts.py
│
├── models/
│   └── model.pkl
│
├── main.py
│
└── dashboard/
```

---

# Core Features

TrendProject provides the following capabilities:

### Market Trend Detection

Detects uptrend, downtrend, or sideways market using pure price structure.

### Machine Learning Prediction

Predicts whether tomorrow's price will go up or down.

### Renko Noise Filtering

Uses Renko bricks to remove market noise and detect trend strength.

### Indicator Summary

Aggregates multiple technical indicators into Buy/Sell/Neutral signals.

### Interactive Charts

Provides TradingView-like charts with zoom, pan, and hover tools.

### Forecasting

Uses Facebook Prophet to project future price movement.

---

# Data Pipeline

Market data is collected from **Yahoo Finance**.

Data fields:

```
Open
High
Low
Close
Volume
Adj Close
```

Supported intervals include:

```
1m
5m
15m
1h
1d
1wk
1mo
```

The system automatically:

1. Fetches OHLCV data
2. Normalizes column names
3. Sorts timestamps
4. Removes invalid rows
5. Caches results locally

---

# Technical Indicators Engine

The indicator processor generates all technical indicators required by:

* ML model
* dashboard charts
* indicator summary

Indicators include:

### Moving Averages

```
SMA 10
SMA 20
SMA 50
SMA 200
EMA 10
EMA 20
EMA 50
```

### Momentum Indicators

```
RSI (14)
Momentum (5)
Momentum (10)
```

### Volatility Indicators

```
ATR (14)
Rolling volatility (20)
```

### MACD

```
MACD Line
MACD Signal
MACD Histogram
```

### Additional Features

```
Returns
Regression slope
Price/average ratios
```

These indicators are used as **features for machine learning**.

---

# Market Structure Trend Detection

Trend detection uses **pure price action**, not indicators.

The algorithm checks for **higher highs and higher lows**.

Uptrend definition:

```
High3 > High2 > High1
Low3 > Low2 > Low1
```

Downtrend definition:

```
High3 < High2 < High1
Low3 < Low2 < Low1
```

The detector scans the last **N candles** (lookback window).

Example:

```
lookback = 252 candles
```

Confidence score:

```
confidence = dominant_structures / total_structures
```

Example:

```
UP structures = 18
DOWN structures = 11

confidence = 18 / 29 = 0.62
```

---

# Machine Learning Model

The ML system predicts **next-day price direction**.

Target definition:

```
Target = 1 if Close(t+1) > Close(t)
Target = 0 otherwise
```

Features include:

```
SMA
EMA
RSI
MACD
Momentum
ATR
Volatility
Slope
Price ratios
Returns
```

The model used is:

```
RandomForestClassifier
```

Training parameters:

```
n_estimators = 300
max_depth = 10
```

Output example:

```
Prediction: UP
Confidence: 0.56
```

---

# Renko Trend Detection

Renko charts remove market noise.

Each brick represents a **fixed price movement**.

Brick size methods:

```
ATR-based
Fixed percentage
Volatility-based
```

Trend is determined by the ratio:

```
up_bricks / total_bricks
```

Example:

```
UP bricks = 80
DOWN bricks = 36

trend = UPTREND
confidence = 0.85
```

---

# Prophet Forecasting

The Prophet module forecasts **future prices**.

It models:

```
trend
weekly seasonality
yearly seasonality
```

Outputs include:

```
forecast price
confidence intervals
trend direction
```

Example output:

```
Trend: BULLISH
Confidence: MEDIUM
```

---

# Technical Summary System

Indicators are converted into signals:

```
Strong Buy
Buy
Neutral
Sell
Strong Sell
```

Signals are aggregated across:

```
Oscillators
Moving averages
```

The dashboard displays a **gauge indicator** summarizing the overall signal.

---

# Visualization Layer

The dashboard is built with **Streamlit + Plotly**.

Charts include:

### Candlestick Chart

Displays:

```
OHLC candles
SMA overlays
hover statistics
```

### RSI Chart

Includes standard thresholds:

```
70 = Overbought
30 = Oversold
```

### MACD Chart

Displays:

```
MACD line
Signal line
Histogram
```

### Renko Chart

Shows:

```
Renko bricks
price trend
timestamps
```

---

# Caching System

To avoid repeated API calls, data is cached locally.

Cache features:

```
pickle storage
timestamp validation
automatic expiration
atomic writes
```

Cache duration:

```
1 day
```

---

# Model Training Pipeline

The training script:

```
project/main.py
```

Steps:

1. Download 3 years of market data
2. Compute indicators
3. Generate target labels
4. Train RandomForest model
5. Evaluate accuracy
6. Save model to disk

Saved model:

```
project/models/model.pkl
```

Payload structure:

```
{
  "model": trained_model,
  "features": feature_list
}
```

---

# Dashboard Features

The dashboard provides:

### Market Overview

Displays:

```
company information
latest price
price change
sector
exchange
```

### Trend Signals

```
Trend Detector
ML Prediction
Renko Trend
```

### Technical Summary

Aggregated signal strength across indicators.

### Charts

```
candlestick
RSI
MACD
volume
Renko
SMA

### Data Inspection

Users can view the full processed dataset.

---



Install dependencies:

```
pip install -r requirements.txt
```

---

# Usage

Train the model:

```
python project/main.py
```

Run the dashboard:

```
streamlit run dashboard.py
```

---

# Future Improvements

Planned improvements include:

* LSTM deep learning models
* sentiment analysis integration
* crypto and forex support
* portfolio tracking
* backtesting engine
* reinforcement learning strategies
* risk management module

---

# Author

TrendProject is a quantitative trading analytics project designed to explore the intersection of:

```
machine learning
market structure analysis
algorithmic trading
data visualization
```

---
