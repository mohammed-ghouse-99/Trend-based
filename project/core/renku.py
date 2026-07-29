# project/core/renko.py
"""
Renko Trend Detector with timestamps
Pure price-based trend detection using Renko bricks with time tracking.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class RenkoBrick:
    """Represents a single Renko brick with timestamp."""
    direction: str  # "UP", "DOWN", or "FIRST"
    price: float    # Closing price of the brick
    timestamp: Any  # pandas Timestamp or datetime
    
    def to_dict(self):
        return {
            'direction': self.direction,
            'price': self.price,
            'timestamp': self.timestamp
        }


class RenkoDetector:
    """
    Detects trend using Renko bricks with timestamps.
    
    Renko charts filter out noise and focus on significant price movements.
    Each brick (box) represents a fixed price movement at a specific time.
    """
    
    def __init__(self, brick_size_method: str = "atr", brick_period: int = 20, 
                 atr_period: int = 14, brick_multiplier: float = 1.0):
        """
        Initialize Renko detector.
        
        Parameters:
        -----------
        brick_size_method : str
            Method to calculate brick size: 
            - "atr": Use Average True Range (adaptive)
            - "fixed": Use percentage of current price
            - "auto": Auto-calculate based on price volatility
        brick_period : int
            Period for calculating brick size
        atr_period : int
            Period for ATR calculation (if using ATR method)
        brick_multiplier : float
            Multiplier for brick size (1.0 = standard)
        """
        self.brick_size_method = brick_size_method
        self.brick_period = brick_period
        self.atr_period = atr_period
        self.brick_multiplier = brick_multiplier
        self._brick_size = None
        self._bricks = []  # Store bricks as RenkoBrick objects
        
    def _calculate_true_range(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate True Range for ATR."""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """Calculate Average True Range."""
        true_range = self._calculate_true_range(high, low, close)
        atr = true_range.rolling(window=self.atr_period).mean().iloc[-1]
        return float(atr) if not pd.isna(atr) else 0.0
    
    def _calculate_brick_size(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """Calculate optimal brick size based on selected method."""
        if self.brick_size_method == "atr":
            # Use ATR as brick size
            atr_value = self._calculate_atr(high, low, close)
            if atr_value > 0:
                brick_size = atr_value * self.brick_multiplier
            else:
                # Fallback to percentage if ATR fails
                avg_price = close.mean()
                brick_size = avg_price * 0.01  # 1% of average price
        
        elif self.brick_size_method == "fixed":
            # Fixed percentage of current price
            current_price = close.iloc[-1]
            brick_size = current_price * 0.01  # 1% of current price
        
        elif self.brick_size_method == "auto":
            # Auto-calculate based on price volatility
            price_range = high.max() - low.min()
            if len(close) > self.brick_period:
                recent_prices = close.iloc[-self.brick_period:]
                volatility = recent_prices.std()
                brick_size = volatility * 1.5  # 1.5x volatility
            else:
                brick_size = price_range * 0.02  # 2% of price range
        
        else:
            raise ValueError(f"Unknown brick size method: {self.brick_size_method}")
        
        # Ensure minimum brick size (avoid too small bricks)
        min_brick = close.mean() * 0.002  # 0.2% minimum
        brick_size = max(brick_size, min_brick)
        
        # Round to reasonable decimal places
        if brick_size >= 10:
            brick_size = round(brick_size, 1)
        elif brick_size >= 1:
            brick_size = round(brick_size, 2)
        else:
            brick_size = round(brick_size, 4)
        
        self._brick_size = brick_size
        return brick_size
    
    def _build_renko_bricks(self, df: pd.DataFrame, close: pd.Series, brick_size: float) -> Tuple[int, int]:
        """
        Build Renko bricks with timestamps.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Original dataframe with index as timestamps
        close : pd.Series
            Close prices
        brick_size : float
            Size of each brick
            
        Returns:
        --------
        tuple: (up_bricks, down_bricks)
        """
        if len(close) < 2:
            return 0, 0
        
        bricks = []
        current_brick = None
        up_bricks = 0
        down_bricks = 0
        
        # Get timestamps from dataframe index
        timestamps = df.index
        
        for idx, (timestamp, price) in enumerate(zip(timestamps, close)):
            if current_brick is None:
                # First brick
                current_brick = price
                bricks.append(RenkoBrick(
                    direction="FIRST",
                    price=current_brick,
                    timestamp=timestamp
                ))
                continue
            
            # Check if price moved enough for a new brick
            price_diff = price - current_brick
            
            if price_diff >= brick_size:
                # Up brick(s)
                bricks_required = int(price_diff // brick_size)
                for _ in range(bricks_required):
                    current_brick += brick_size
                    bricks.append(RenkoBrick(
                        direction="UP",
                        price=current_brick,
                        timestamp=timestamp  # Brick time = candle time
                    ))
                    up_bricks += 1
            
            elif price_diff <= -brick_size:
                # Down brick(s)
                bricks_required = int(abs(price_diff) // brick_size)
                for _ in range(bricks_required):
                    current_brick -= brick_size
                    bricks.append(RenkoBrick(
                        direction="DOWN",
                        price=current_brick,
                        timestamp=timestamp  # Brick time = candle time
                    ))
                    down_bricks += 1
        
        # Store bricks for charting
        self._bricks = bricks
        
        return up_bricks, down_bricks
    
    @property
    def bricks(self) -> List[RenkoBrick]:
        """Get the list of Renko bricks for charting."""
        return self._bricks
    
    def get_bricks_as_dicts(self) -> List[Dict]:
        """Get bricks as dictionary for easy serialization."""
        return [brick.to_dict() for brick in self._bricks]
    
    def _determine_trend(self, up_bricks: int, down_bricks: int, total_bricks: int) -> str:
        """Determine trend based on brick count ratio."""
        if total_bricks == 0:
            return "SIDEWAYS"
        
        up_ratio = up_bricks / total_bricks
        down_ratio = down_bricks / total_bricks
        
        # Strong trend criteria
        if up_ratio >= 0.7:
            return "UPTREND"
        elif down_ratio >= 0.7:
            return "DOWNTREND"
        elif up_ratio >= 0.55:
            return "WEAK_UPTREND"
        elif down_ratio >= 0.55:
            return "WEAK_DOWNTREND"
        else:
            return "SIDEWAYS"
    
    def detect_trend(self, df: pd.DataFrame) -> Dict:
        """
        Detect trend using Renko bricks with timestamps.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Must contain 'High', 'Low', 'Close' columns and datetime index
            
        Returns:
        --------
        dict: {
            'trend': str (UPTREND/DOWNTREND/SIDEWAYS/WEAK_UPTREND/WEAK_DOWNTREND),
            'brick_size': float,
            'total_bricks': int,
            'up_bricks': int,
            'down_bricks': int,
            'brick_ratio': float (up_bricks/total_bricks),
            'confidence': float (0-1),
            'first_brick_time': timestamp or None,
            'last_brick_time': timestamp or None
        }
        """
        # Validate input
        required_cols = ['High', 'Low', 'Close']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"DataFrame must contain '{col}' column")
        
        # Extract price series
        high = pd.to_numeric(df['High'], errors='coerce')
        low = pd.to_numeric(df['Low'], errors='coerce')
        close = pd.to_numeric(df['Close'], errors='coerce')
        
        # Drop NaN values
        valid_mask = ~(high.isna() | low.isna() | close.isna())
        df_valid = df[valid_mask].copy()
        high = high[valid_mask]
        low = low[valid_mask]
        close = close[valid_mask]
        
        if len(close) < 2:
            return {
                'trend': 'SIDEWAYS',
                'brick_size': 0.0,
                'total_bricks': 0,
                'up_bricks': 0,
                'down_bricks': 0,
                'brick_ratio': 0.5,
                'confidence': 0.0,
                'first_brick_time': None,
                'last_brick_time': None
            }
        
        # Calculate brick size
        brick_size = self._calculate_brick_size(high, low, close)
        
        # Build Renko bricks with timestamps
        up_bricks, down_bricks = self._build_renko_bricks(df_valid, close, brick_size)
        total_bricks = up_bricks + down_bricks
        
        # Determine trend
        trend = self._determine_trend(up_bricks, down_bricks, total_bricks)
        
        # Calculate confidence
        if total_bricks > 0:
            ratio = max(up_bricks, down_bricks) / total_bricks
            confidence = min(ratio * 1.5, 1.0)  # Scale to 0-1
        else:
            confidence = 0.0
        
        # Get first and last brick times
        first_brick_time = None
        last_brick_time = None
        if self._bricks:
            first_brick_time = self._bricks[0].timestamp
            last_brick_time = self._bricks[-1].timestamp
        
        # Prepare result
        result = {
            'trend': trend,
            'brick_size': brick_size,
            'total_bricks': total_bricks,
            'up_bricks': up_bricks,
            'down_bricks': down_bricks,
            'brick_ratio': up_bricks / total_bricks if total_bricks > 0 else 0.5,
            'confidence': round(confidence, 2),
            'first_brick_time': first_brick_time,
            'last_brick_time': last_brick_time
        }
        
        return result


# Convenience function for quick usage
def detect_renko_trend(df: pd.DataFrame, brick_size_method: str = "atr") -> Dict:
    """
    Quick function to detect Renko trend.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Must contain 'High', 'Low', 'Close' columns
    brick_size_method : str
        Method for brick size calculation
        
    Returns:
    --------
    dict: Renko trend detection result
    """
    detector = RenkoDetector(brick_size_method=brick_size_method)
    return detector.detect_trend(df)


if __name__ == "__main__":
    # Quick test
    print(" RenkoDetector with timestamps is ready!")
    print(" Each brick now has: direction, price, timestamp")