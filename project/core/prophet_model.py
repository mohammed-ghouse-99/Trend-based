"""
Prophet Model for Stock Price Forecasting - ROBUST VERSION
Single Responsibility: ONLY forecast future prices based on historical close prices
"""

from prophet import Prophet
import pandas as pd
from typing import Tuple, Dict, Any, Optional
import numpy as np


class StockProphet:
    """
    Prophet model wrapper specifically for stock price forecasting.
    
    Responsibilities:
    1. Take historical date and close price only
    2. Model trend + weekly/yearly seasonality
    3. Generate future forecast with confidence intervals
    4. Return raw forecast data (NO decisions)
    
    What it does NOT do:
    - No buy/sell signals
    - No accuracy metrics
    - No indicator calculations
    - No caching/saving
    """
    
    def __init__(self, 
                 weekly_seasonality: bool = True,
                 yearly_seasonality: bool = True,
                 daily_seasonality: bool = False):
        """
        Configure Prophet model for stock data.
        
        Parameters:
        -----------
        weekly_seasonality : bool
            Consider weekly patterns (Mon-Fri behavior)
        yearly_seasonality : bool
            Consider yearly patterns (seasonal trends)
        daily_seasonality : bool
            For stocks, daily patterns are noise (avoid)
        """
        # Create Prophet model with stock-appropriate settings
        self.model = Prophet(
            weekly_seasonality=weekly_seasonality,
            yearly_seasonality=yearly_seasonality,
            daily_seasonality=daily_seasonality,
            changepoint_prior_scale=0.05,  # Less sensitive to small changes
            seasonality_prior_scale=10.0,  # Capture clear seasonal patterns
            interval_width=0.8  # 80% confidence interval
        )
        
        # Store configuration for reference
        self.config = {
            'weekly_seasonality': weekly_seasonality,
            'yearly_seasonality': yearly_seasonality,
            'daily_seasonality': daily_seasonality
        }
        
        self.is_fitted = False
    
    def prepare_data(self, historical_data: pd.DataFrame) -> pd.DataFrame:
        """
        Translate stock data to Prophet language.
        
        Input: DataFrame with Date index and Close column
        Output: DataFrame with 'ds' and 'y' columns
        
        Note: Only uses Date and Close, ignores all other columns
        """
        # Create a copy to avoid modifying original
        df = historical_data.copy()
        
        # Reset index to get Date as column if it's the index
        if df.index.name is not None:
            df = df.reset_index()
        
        # ✅ DEFENSIVE CODING: Get FIRST column as date (whatever it's named)
        date_col = df.columns[0]  # First column = Date/Datetime
        
        # ✅ Handle Close column - check if exists
        if 'Close' not in df.columns:
            raise ValueError("'Close' column not found in data")
        
        prophet_df = pd.DataFrame({
            'ds': pd.to_datetime(df[date_col]),  # Convert to datetime
            'y': df['Close'].astype(float)       # Ensure float type
        })
        
        # Remove any NaN values (Prophet requirement)
        prophet_df = prophet_df.dropna()
        
        # Sort by date (important for time series)
        prophet_df = prophet_df.sort_values('ds')
        
        return prophet_df
    
    def fit(self, historical_data: pd.DataFrame) -> None:
        """
        Learn patterns from historical data.
        
        This is curve fitting + decomposition, NOT ML training.
        No train/test split needed for time series forecasting.
        """
        try:
            # Prepare data for Prophet
            prophet_df = self.prepare_data(historical_data)
            
            # Check if we have enough data
            if len(prophet_df) < 30:
                raise ValueError(f"Insufficient data for Prophet. Need at least 30 rows, got {len(prophet_df)}")
            
            # Fit the model (learn patterns)
            self.model.fit(prophet_df)
            
            self.is_fitted = True
            
            # Store last date for reference
            self.last_training_date = prophet_df['ds'].max()
            
        except Exception as e:
            raise ValueError(f"Prophet fitting failed: {str(e)}")
    
    def forecast(self, periods: int = 30) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate future price forecast.
        
        Parameters:
        -----------
        periods : int
            Number of future periods to forecast (default: 30 days)
            
        Returns:
        --------
        forecast_df : pd.DataFrame
            Raw forecast with columns: ds, yhat, yhat_lower, yhat_upper
        forecast_info : dict
            Metadata about the forecast
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before forecasting")
        
        try:
            # Create future dataframe
            future_df = self.model.make_future_dataframe(periods=periods, freq='D')
            
            # Generate forecast
            forecast_df = self.model.predict(future_df)
            
            # Extract only the future forecast (not historical fit)
            last_training_idx = forecast_df[forecast_df['ds'] == self.last_training_date].index[0]
            future_forecast = forecast_df.iloc[last_training_idx + 1:]
            
            # Select only essential columns
            essential_columns = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
            future_forecast = future_forecast[essential_columns].reset_index(drop=True)
            
            # Prepare forecast information
            forecast_info = {
                'forecast_periods': periods,
                'last_training_date': self.last_training_date,
                'first_forecast_date': future_forecast['ds'].min(),
                'last_forecast_date': future_forecast['ds'].max(),
                'model_config': self.config,
                'data_points_used': self.model.history.shape[0]
            }
            
            return future_forecast, forecast_info
            
        except Exception as e:
            raise ValueError(f"Prophet forecasting failed: {str(e)}")
    
    def get_forecast_trend(self, forecast_df: pd.DataFrame) -> Tuple[str, str]:
        """
        Convert raw forecast to simple trend direction with confidence.
        
        Returns:
        --------
        trend : str
            Simple trend direction (BULLISH/BEARISH/NEUTRAL/MIXED)
        confidence : str
            Confidence level (HIGH/MEDIUM/LOW)
        """
        if forecast_df is None or len(forecast_df) < 2:
            return "INSUFFICIENT_DATA", "LOW"
        
        try:
            # Calculate trend from forecast
            start_price = forecast_df['yhat'].iloc[0]
            end_price = forecast_df['yhat'].iloc[-1]
            pct_change = ((end_price - start_price) / start_price) * 100
            
            # Calculate confidence band width
            avg_confidence_width = (forecast_df['yhat_upper'] - forecast_df['yhat_lower']).mean()
            price_range = forecast_df['yhat'].max() - forecast_df['yhat'].min()
            confidence_ratio = avg_confidence_width / price_range if price_range > 0 else 1
            
            # Determine confidence
            if confidence_ratio < 0.2:
                confidence_level = "HIGH"
            elif confidence_ratio < 0.4:
                confidence_level = "MEDIUM"
            else:
                confidence_level = "LOW"
            
            # Determine trend
            if abs(pct_change) < 2.0:  # Less than 2% change
                trend = "NEUTRAL"
            elif pct_change > 5.0:  # Strong bullish
                trend = "BULLISH"
            elif pct_change > 0:  # Mild bullish
                trend = "MILDLY_BULLISH"
            elif pct_change < -5.0:  # Strong bearish
                trend = "BEARISH"
            else:  # Mild bearish
                trend = "MILDLY_BEARISH"
            
            return trend, confidence_level
            
        except Exception:
            return "ERROR", "LOW"


# Factory function with robust error handling
def create_prophet_forecast(
    historical_data: pd.DataFrame,
    forecast_periods: int = 30
) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]], str, str]:
    """
    One-shot function to create forecast.
    
    This is the main interface for the dashboard to use.
    
    Returns:
    --------
    forecast_df : Raw forecast data (or None if error)
    forecast_info : Metadata (or None if error)
    trend : Simple trend string
    confidence : Confidence level string
    """
    try:
        # Check if we have valid data
        if historical_data is None or historical_data.empty:
            return None, None, "NO_DATA", "LOW"
        
        if 'Close' not in historical_data.columns:
            return None, None, "MISSING_CLOSE", "LOW"
        
        # Initialize Prophet for stocks
        prophet = StockProphet(
            weekly_seasonality=True,  # Capture weekly patterns
            yearly_seasonality=True,  # Capture yearly patterns
            daily_seasonality=False   # Daily patterns are noise for stocks
        )
        
        # Fit the model
        prophet.fit(historical_data)
        
        # Generate forecast
        forecast_df, forecast_info = prophet.forecast(forecast_periods)
        
        # Get simple trend and confidence
        trend, confidence = prophet.get_forecast_trend(forecast_df)
        
        return forecast_df, forecast_info, trend, confidence
        
    except Exception as e:
        print(f"⚠️ Prophet forecast error: {str(e)}")
        return None, None, "ERROR", "LOW"