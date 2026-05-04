from typing import Dict
import pandas as pd


class TrendDetector:
    """
    PURE market-structure based trend detector.

    Rules:
    - Uses ONLY High & Low price action
    - No indicators
    - No ML
    - Trend is derived from HH/HL vs LH/LL dominance
    - Lookback (number of candles) is USER-CONTROLLED
    """

    def __init__(self, lookback: int = 500):
        """
        lookback : number of recent candles to analyze
        NOTE: This value MUST be passed from dashboard.
        """
        self.lookback = int(lookback)

    # -------------------------------------------------
    # STRUCTURE CHECKS (3-bar logic)
    # -------------------------------------------------
    @staticmethod
    def _higher_highs_lows(window: pd.DataFrame) -> bool:
        highs = window["High"].values
        lows = window["Low"].values

        return (
            highs[2] > highs[1] > highs[0] and
            lows[2] > lows[1] > lows[0]
        )

    @staticmethod
    def _lower_highs_lows(window: pd.DataFrame) -> bool:
        highs = window["High"].values
        lows = window["Low"].values

        return (
            highs[2] < highs[1] < highs[0] and
            lows[2] < lows[1] < lows[0]
        )

    # -------------------------------------------------
    # MAIN API
    # -------------------------------------------------
    def detect_trend(self, df: pd.DataFrame) -> Dict[str, object]:
        """
        Returns:
        {
            "trend": "UPTREND" | "DOWNTREND" | "SIDEWAYS" | "UNKNOWN",
            "confidence": float (0–1),
            "based_on_bars": int
        }
        """

        if df is None or len(df) < 10:
            return {
                "trend": "UNKNOWN",
                "confidence": 0.0,
                "based_on_bars": 0
            }

        # 🔥 USE EXACT LOOKBACK FROM DASHBOARD
        df = df.tail(self.lookback)

        up_count = 0
        down_count = 0

        # Sliding 3-bar structure scan
        for i in range(2, len(df)):
            window = df.iloc[i - 2 : i + 1]

            if self._higher_highs_lows(window):
                up_count += 1
            elif self._lower_highs_lows(window):
                down_count += 1

        total = up_count + down_count

        # -------------------------------------------------
        # FINAL DECISION
        # -------------------------------------------------
        if total == 0:
            trend = "SIDEWAYS"
            confidence = 0.30

        elif up_count > down_count:
            trend = "UPTREND"
            confidence = round(up_count / total, 2)

        elif down_count > up_count:
            trend = "DOWNTREND"
            confidence = round(down_count / total, 2)

        else:
            trend = "SIDEWAYS"
            confidence = 0.50

        return {
            "trend": trend,
            "confidence": confidence,
            "based_on_bars": len(df)
        }
