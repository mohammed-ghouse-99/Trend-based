import pandas as pd
from project.core.utils import require_columns


class IndicatorSummary:
    """
    Indicator-based confirmation layer.
    DOES NOT decide trend.
    ONLY gives BUY / SELL / NEUTRAL per indicator.
    """

    # -------------------------
    # Individual indicator rules
    # -------------------------
    @staticmethod
    def rsi_signal(rsi: float) -> str:
        if rsi > 60:
            return "BUY"
        if rsi < 40:
            return "SELL"
        return "NEUTRAL"

    @staticmethod
    def macd_signal(macd_hist: float) -> str:
        return "BUY" if macd_hist > 0 else "SELL"

    @staticmethod
    def momentum_signal(momentum: float) -> str:
        return "BUY" if momentum > 0 else "SELL"

    @staticmethod
    def sma_signal(close: float, sma: float) -> str:
        return "BUY" if close > sma else "SELL"

    # -------------------------
    # Main summary function
    # -------------------------
    def summarize(self, df: pd.DataFrame) -> dict:
        require_columns(
            df,
            [
                "Close",
                "RSI_14",
                "MACD_HIST",
                "MOMENTUM_10",
                "SMA_10",
                "SMA_20",
                "SMA_25",
                "SMA_50",
            ]
        )

        last = df.iloc[-1]
        close = float(last["Close"])

        signals = {
            "RSI": self.rsi_signal(last["RSI_14"]),
            "MACD": self.macd_signal(last["MACD_HIST"]),
            "MOMENTUM": self.momentum_signal(last["MOMENTUM_10"]),
            "SMA_10": self.sma_signal(close, last["SMA_10"]),
            "SMA_20": self.sma_signal(close, last["SMA_20"]),
            "SMA_25": self.sma_signal(close, last["SMA_25"]),
            "SMA_50": self.sma_signal(close, last["SMA_50"]),
        }

        values = {
            "RSI": round(last["RSI_14"], 2),
            "MACD_HIST": round(last["MACD_HIST"], 4),
            "MOMENTUM_10": round(last["MOMENTUM_10"], 2),
            "SMA_10": round(last["SMA_10"], 2),
            "SMA_20": round(last["SMA_20"], 2),
            "SMA_50": round(last["SMA_50"], 2),
        }

        return {
            "signals": signals,
            "values": values
        }
