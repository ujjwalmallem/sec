"""
Utility Functions
Helper functions for the whale scanner
"""

import logging
from datetime import datetime, time
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def format_large_number(num: float) -> str:
    """
    Format large numbers with K, M, B suffixes

    Args:
        num: Number to format

    Returns:
        Formatted string
    """
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.2f}K"
    else:
        return f"{num:.0f}"


def calculate_zscore(value: float, series: pd.Series) -> float:
    """
    Calculate z-score (standard deviations from mean)

    Args:
        value: Current value
        series: Historical series

    Returns:
        Z-score
    """
    try:
        mean = series.mean()
        std = series.std()

        if std == 0:
            return 0.0

        zscore = (value - mean) / std
        return round(zscore, 2)

    except Exception as e:
        logger.error(f"Error calculating z-score: {e}")
        return 0.0


def is_market_hours(dt: Optional[datetime] = None) -> bool:
    """
    Check if datetime is within regular market hours (9:30 AM - 4:00 PM ET)

    Args:
        dt: Datetime to check (defaults to now)

    Returns:
        True if within market hours
    """
    if dt is None:
        dt = datetime.now()

    # Check weekday (Mon-Fri = 0-4)
    if dt.weekday() >= 5:
        return False

    # Check time (9:30 AM - 4:00 PM ET)
    market_open = time(9, 30)
    market_close = time(16, 0)

    current_time = dt.time()

    return market_open <= current_time <= market_close


def calculate_percentage_change(current: float, previous: float) -> float:
    """
    Calculate percentage change

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Percentage change
    """
    if previous == 0:
        return 0.0

    return ((current - previous) / previous) * 100


def get_moneyness_label(strike: float, underlying: float) -> str:
    """
    Get moneyness label for an option

    Args:
        strike: Strike price
        underlying: Underlying price

    Returns:
        Moneyness label (ITM, ATM, OTM)
    """
    diff = abs(strike - underlying) / underlying * 100

    if diff <= 1:  # Within 1%
        return "ATM"
    elif strike < underlying:
        return "ITM"  # For calls
    else:
        return "OTM"


def rank_value_in_range(value: float, min_val: float, max_val: float) -> float:
    """
    Calculate rank (0-100) of value in range

    Args:
        value: Current value
        min_val: Minimum of range
        max_val: Maximum of range

    Returns:
        Rank (0-100)
    """
    if max_val == min_val:
        return 50.0

    rank = ((value - min_val) / (max_val - min_val)) * 100
    return round(max(0, min(100, rank)), 2)


def calculate_moving_average(series: pd.Series, periods: int) -> float:
    """
    Calculate simple moving average

    Args:
        series: Data series
        periods: Number of periods

    Returns:
        Moving average
    """
    return series.tail(periods).mean()


def detect_volume_spike(current_volume: int, avg_volume: float,
                       threshold: float = 2.0) -> bool:
    """
    Detect if current volume is a spike

    Args:
        current_volume: Current volume
        avg_volume: Average volume
        threshold: Multiplier threshold (default 2x)

    Returns:
        True if volume spike detected
    """
    if avg_volume == 0:
        return False

    return current_volume >= (avg_volume * threshold)


def format_timestamp(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format timestamp

    Args:
        dt: Datetime to format (defaults to now)
        fmt: Format string

    Returns:
        Formatted timestamp
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime(fmt)


def parse_expiration(exp_str: str) -> datetime:
    """
    Parse expiration string to datetime

    Args:
        exp_str: Expiration string (YYYYMMDD)

    Returns:
        Datetime object
    """
    return datetime.strptime(exp_str, '%Y%m%d')


def calculate_dte(expiration: str) -> int:
    """
    Calculate days to expiration

    Args:
        expiration: Expiration string (YYYYMMDD)

    Returns:
        Days to expiration
    """
    exp_date = parse_expiration(expiration)
    today = datetime.now()
    return (exp_date - today).days


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division fails

    Returns:
        Result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except:
        return default


def filter_outliers(series: pd.Series, n_std: float = 3.0) -> pd.Series:
    """
    Filter outliers using z-score method

    Args:
        series: Data series
        n_std: Number of standard deviations

    Returns:
        Filtered series
    """
    mean = series.mean()
    std = series.std()

    if std == 0:
        return series

    z_scores = np.abs((series - mean) / std)
    return series[z_scores <= n_std]


def get_option_label(strike: float, right: str, expiration: str) -> str:
    """
    Get formatted option label

    Args:
        strike: Strike price
        right: 'C' or 'P'
        expiration: Expiration string

    Returns:
        Option label (e.g., "450C 12/31")
    """
    exp_date = parse_expiration(expiration)
    exp_formatted = exp_date.strftime('%m/%d')

    right_label = "C" if right == "C" else "P"

    return f"{strike:.0f}{right_label} {exp_formatted}"


def categorize_dte(dte: int) -> str:
    """
    Categorize DTE into buckets

    Args:
        dte: Days to expiration

    Returns:
        Category label
    """
    if dte == 0:
        return "0DTE"
    elif dte <= 2:
        return "1-2 DTE"
    elif dte <= 7:
        return "Weekly"
    elif dte <= 30:
        return "Monthly"
    elif dte <= 90:
        return "Quarterly"
    else:
        return "LEAPS"


def color_text(text: str, color: str) -> str:
    """
    Add ANSI color codes to text

    Args:
        text: Text to color
        color: Color name (red, green, yellow, blue, etc.)

    Returns:
        Colored text
    """
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }

    color_code = colors.get(color.lower(), colors['reset'])
    return f"{color_code}{text}{colors['reset']}"


def validate_symbol(symbol: str) -> bool:
    """
    Validate ticker symbol format

    Args:
        symbol: Ticker symbol

    Returns:
        True if valid
    """
    if not symbol:
        return False

    # Basic validation: uppercase letters, 1-5 characters
    return symbol.isalpha() and symbol.isupper() and 1 <= len(symbol) <= 5


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
