import math
import pandas as pd
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def now_ist() -> datetime:
    return datetime.now(IST)

def today_str() -> str:
    return now_ist().strftime("%d %b %Y")

def timestamp_str() -> str:
    return now_ist().strftime("%d %b %Y, %I:%M %p IST")

def safe_scalar(x) -> float:
    """Extract a plain Python float from a pandas Series, DataFrame, or numpy scalar."""
    try:
        if isinstance(x, (pd.Series, pd.DataFrame)):
            arr = x.to_numpy().ravel()
            return float(arr[-1])
        return float(x)
    except Exception:
        return float("nan")

def fmt_pct(x, plus: bool = False) -> str:
    """Format a float as a percentage string. Returns 'N/A' for nan/None."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/A"
    return f"{x:+.2f}%" if plus else f"{x:.2f}%"

def normalize_ohlc(df: "pd.DataFrame") -> "pd.DataFrame":
    """Flatten yfinance MultiIndex columns if present."""
    import pandas as pd
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df