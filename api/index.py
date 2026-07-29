import os
import sys
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np
import joblib
from fastapi import FastAPI, Request, Form, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jose import jwt, JWTError
from jinja2 import Environment, FileSystemLoader

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from project.data.collector import get_data
from project.data.storage import load_cache, save_cache
from project.data.processor import add_indicators
from project.core.trend_detector import TrendDetector
from project.core.renku import RenkoDetector
from project.visual.charts import (
    plot_candlestick, plot_rsi, plot_macd,
    plot_volume, plot_renko,
)
from project.core.halal.pipeline import screen_stock

app = FastAPI()
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))

def render_template(name: str, **context):
    template = _jinja_env.get_template(name)
    return HTMLResponse(template.render(**context))

SECRET_KEY = os.environ.get("SECRET_KEY", "trend-project-secret-change-in-prod")
ALGORITHM = "HS256"
MODEL_PATH = os.path.join(ROOT, "project", "models", "model.pkl")

RSI_BUY = 30; RSI_SELL = 70
STRONG_MULTIPLIER = 1.02; STRONG_MACD_STD_MULT = 1.5
ACTION_TO_VAL = {"Strong Sell": 10, "Sell": 30, "Neutral": 50, "Buy": 70, "Strong Buy": 90, "N/A": 50}

def make_token():
    return jwt.encode({"sub": "admin", "iat": datetime.utcnow()}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> bool:
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False

def get_company_info(ticker_symbol: str):
    import yfinance as yf
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        return {
            "name": info.get("longName", ticker_symbol),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "logo_url": info.get("logo_url", ""),
            "website": info.get("website", ""),
            "summary": info.get("longBusinessSummary", ""),
            "market_cap": info.get("marketCap"),
            "country": info.get("country", "N/A"),
        }
    except Exception:
        return {"name": ticker_symbol, "sector": "N/A", "industry": "N/A", "exchange": "N/A",
                "logo_url": "", "website": "", "summary": "", "market_cap": None, "country": "N/A"}

def load_trained_model(model_path: str):
    if not os.path.exists(model_path):
        return None, None
    loaded = joblib.load(model_path)
    if isinstance(loaded, dict) and "model" in loaded:
        return loaded["model"], loaded.get("features", None)
    return loaded, None

def action_from_rsi(val):
    if np.isnan(val): return "N/A"
    if val < RSI_BUY: return "Buy"
    if val > RSI_SELL: return "Sell"
    return "Neutral"

def action_from_macd_hist(val, hist_std):
    if np.isnan(val): return "N/A"
    if val > 0: return "Strong Buy" if abs(val) > (STRONG_MACD_STD_MULT * max(hist_std, 1e-9)) else "Buy"
    if val < 0: return "Strong Sell" if abs(val) > (STRONG_MACD_STD_MULT * max(hist_std, 1e-9)) else "Sell"
    return "Neutral"

def action_from_momentum(val):
    if np.isnan(val): return "N/A"
    return "Buy" if val > 0 else ("Sell" if val < 0 else "Neutral")

def action_from_return(val):
    return action_from_momentum(val)

def action_from_ma(price, ma):
    if np.isnan(ma) or np.isnan(price): return "N/A"
    if price > ma * STRONG_MULTIPLIER: return "Strong Buy"
    if price > ma: return "Buy"
    if price < ma / STRONG_MULTIPLIER: return "Strong Sell"
    if price < ma: return "Sell"
    return "Neutral"

def aggregate_counts(actions):
    cnt = {"Strong Buy": 0, "Buy": 0, "Neutral": 0, "Sell": 0, "Strong Sell": 0, "N/A": 0}
    for a in actions:
        cnt[a if a in cnt else "N/A"] += 1
    return cnt

def pick_dominant(counts):
    ordered = ["Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell"]
    best = max(ordered, key=lambda k: (counts.get(k, 0), -ordered.index(k)))
    return "Neutral" if sum(counts.get(k, 0) for k in counts if k != "N/A") == 0 else best

@app.get("/")
async def login_page(request: Request):
    token = request.cookies.get("session")
    if token and verify_token(token):
        return RedirectResponse(url="/dashboard")
    return render_template("login.html", error=None)

@app.post("/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        token = make_token()
        resp = RedirectResponse(url="/dashboard", status_code=302)
        resp.set_cookie(key="session", value=token, httponly=True, max_age=86400, samesite="lax")
        return resp
    return render_template("login.html", error="Invalid credentials")

@app.get("/api/logout")
async def logout():
    resp = RedirectResponse(url="/")
    resp.set_cookie(key="session", value="", httponly=True, max_age=0)
    return resp

@app.get("/dashboard")
async def dashboard_page(request: Request):
    token = request.cookies.get("session")
    if not token or not verify_token(token):
        return RedirectResponse(url="/")
    return render_template("dashboard.html")

@app.get("/api/analyze")
async def analyze(
    request: Request,
    ticker: str = Query("AAPL"),
    period: str = Query("3y"),
    interval: str = Query("1d"),
    trend_period: str = Query("1y"),
    use_cache: bool = Query(True),
    refresh: bool = Query(False),
    check_halal: bool = Query(True),
):
    token = request.cookies.get("session")
    if not token or not verify_token(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        company_info = get_company_info(ticker)

        if use_cache and not refresh:
            cached = load_cache(ticker, period, interval)
            df_raw = cached if cached is not None and not cached.empty else get_data(ticker, period, interval)
        else:
            df_raw = get_data(ticker, period, interval)

        if df_raw is None or df_raw.empty:
            return JSONResponse({"error": f"No data returned for {ticker}"}, status_code=400)

        save_cache(df_raw, ticker, period, interval)
        df_proc = add_indicators(df_raw.copy(), dropna=True)
        if "Adj Close" not in df_proc.columns:
            df_proc["Adj Close"] = df_proc["Close"]

        renko_detector = RenkoDetector(brick_size_method="atr")
        renko_result = renko_detector.detect_trend(df_raw)
        renko_bricks = getattr(renko_detector, "bricks", [])
        bricks_json = []
        for b in renko_bricks:
            if hasattr(b, "to_dict"):
                b = b.to_dict()
            bricks_json.append({
                "direction": b.get("direction", ""),
                "timestamp": str(b.get("timestamp", "")),
                "price": float(b.get("price", 0)),
            })

        latest = df_proc.iloc[-1]
        prev = df_proc.iloc[-2] if len(df_proc) > 1 else latest
        last_close = float(latest["Close"])
        prev_close = float(prev["Close"])
        change = last_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0

        halal_res = screen_stock(ticker, use_cache=use_cache) if check_halal else {"status": "SKIPPED"}
        h_status = halal_res.get("status", "ERROR")

        TREND_PERIOD_MAP = {"6mo": 126, "1y": 252, "2y": 504}
        lookback_bars = TREND_PERIOD_MAP.get(trend_period, 252)
        detector = TrendDetector(lookback=lookback_bars)
        trend_result = detector.detect_trend(df_proc)
        trend = trend_result.get("trend", "UNKNOWN") if trend_result else "UNKNOWN"

        ml_pred = 0
        ml_conf = 0.0
        model, feature_list = load_trained_model(MODEL_PATH)
        if model and feature_list:
            try:
                latest_features = df_proc.tail(1)[feature_list].astype(float)
                ml_pred = int(model.predict(latest_features)[0])
                try:
                    proba = model.predict_proba(latest_features)[0]
                    ml_conf = float(proba.max())
                except Exception:
                    ml_conf = 1.0
            except Exception:
                pass

        is_halal = h_status == "COMPLIANT"
        is_non_halal = h_status == "NON_COMPLIANT"
        is_bullish = (trend == "UPTREND") and (ml_pred == 1)

        if is_non_halal:
            decision = {"title": "AVOID - NON-HALAL", "subtitle": "Equity fails Shariah financial or business criteria.", "color": "#ef4444"}
        elif not is_halal:
            decision = {"title": "WAIT - INCOMPLETE DATA", "subtitle": "Missing critical metrics to confirm compliance.", "color": "#f59e0b"}
        elif is_bullish:
            decision = {"title": "HALAL BUY", "subtitle": "Compliant stock with strong bullish technical alignment.", "color": "#10b981"}
        elif trend == "DOWNTREND":
            decision = {"title": "VOID - BEARISH TREND", "subtitle": "Stock is Halal but current market structure is bearish.", "color": "#3b82f6"}
        else:
            decision = {"title": "WATCHLIST", "subtitle": "Stock is Halal; waiting for clearer entry signals.", "color": "#6b7280"}

        close_price = float(latest["Close"]) if "Close" in latest else np.nan
        macd_std = float(df_proc["MACD_HIST"].std()) if "MACD_HIST" in df_proc.columns else 0.0

        osc_items = []
        osc_actions = []
        if "RSI_14" in df_proc.columns:
            v = float(latest["RSI_14"])
            a = action_from_rsi(v)
            osc_items.append({"label": "RSI (14)", "value": round(v, 4), "signal": a})
            osc_actions.append(a)
        if "MACD_HIST" in df_proc.columns:
            v = float(latest["MACD_HIST"])
            a = action_from_macd_hist(v, macd_std)
            osc_items.append({"label": "MACD Histogram", "value": round(v, 4), "signal": a})
            osc_actions.append(a)
        for mcol, label in [("MOMENTUM_5", "Momentum (5)"), ("MOMENTUM_10", "Momentum (10)")]:
            if mcol in df_proc.columns:
                v = float(latest[mcol])
                a = action_from_momentum(v)
                osc_items.append({"label": label, "value": round(v, 4), "signal": a})
                osc_actions.append(a)
        if "RETURNS" in df_proc.columns:
            v = float(latest["RETURNS"])
            a = action_from_return(v)
            osc_items.append({"label": "Returns", "value": round(v, 4), "signal": a})
            osc_actions.append(a)

        ma_items = []
        ma_actions = []
        for col, label in [("SMA_10", "SMA 10"), ("SMA_20", "SMA 20"), ("SMA_50", "SMA 50"),
                           ("SMA_200", "SMA 200"), ("EMA_10", "EMA 10"), ("EMA_20", "EMA 20"), ("EMA_50", "EMA 50")]:
            if col in df_proc.columns:
                v = float(latest[col])
                a = action_from_ma(close_price, v)
                ma_items.append({"label": label, "value": round(v, 4), "signal": a})
                ma_actions.append(a)

        osc_counts = aggregate_counts(osc_actions)
        ma_counts = aggregate_counts(ma_actions)
        combined_actions = osc_actions + ma_actions
        combined_counts = aggregate_counts(combined_actions)

        dominant_osc = pick_dominant(osc_counts)
        dominant_ma = pick_dominant(ma_counts)
        dominant_overall = pick_dominant(combined_counts)

        fig_price = plot_candlestick(df_proc)
        fig_rsi = plot_rsi(df_proc)
        fig_macd = plot_macd(df_proc)
        fig_volume = plot_volume(df_proc)
        fig_renko = plot_renko(renko_bricks, float(renko_result.get("brick_size", 0))) if renko_bricks else None

        return {
            "company": company_info,
            "price": {
                "last": round(last_close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "is_positive": change > 0,
            },
            "decision": decision,
            "halal": {
                "status": h_status,
                "ratios": halal_res.get("ratios", {}),
                "violations": halal_res.get("violations", []),
                "notes": halal_res.get("notes", []),
                "data_completeness": halal_res.get("data_completeness", 0.0),
            },
            "technicals": {
                "trend": trend,
                "trend_confidence": round(trend_result.get("confidence", 0), 2) if trend_result else 0,
                "ml_prediction": ml_pred,
                "ml_confidence": round(ml_conf, 4),
                "renko_trend": renko_result.get("trend", "UNKNOWN"),
                "renko_total_bricks": renko_result.get("total_bricks", 0),
                "renko_up_bricks": renko_result.get("up_bricks", 0),
                "renko_down_bricks": renko_result.get("down_bricks", 0),
                "renko_brick_size": round(float(renko_result.get("brick_size", 0)), 2),
            },
            "gauges": {
                "oscillator": {"value": ACTION_TO_VAL.get(dominant_osc, 50), "label": dominant_osc},
                "ma": {"value": ACTION_TO_VAL.get(dominant_ma, 50), "label": dominant_ma},
                "summary": {"value": ACTION_TO_VAL.get(dominant_overall, 50), "label": dominant_overall},
            },
            "tables": {
                "oscillators": osc_items,
                "moving_averages": ma_items,
            },
            "charts": {
                "candlestick": json.loads(fig_price.to_json()) if fig_price else None,
                "volume": json.loads(fig_volume.to_json()) if fig_volume else None,
                "rsi": json.loads(fig_rsi.to_json()) if fig_rsi else None,
                "macd": json.loads(fig_macd.to_json()) if fig_macd else None,
                "renko": json.loads(fig_renko.to_json()) if fig_renko else None,
            },
            "volume": int(df_proc.iloc[-1]["Volume"]) if "Volume" in df_proc.columns else 0,
            "rows": len(df_proc),
            "ticker": ticker,
            "period": period,
            "interval": interval,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
