"""Shared formatting and data helpers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def ensure_directories() -> None:
    """Create runtime data directories when they do not exist."""
    for directory in (CACHE_DIR, REPORTS_DIR, OUTPUTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def is_available(value: Any) -> bool:
    """Return whether a value can be displayed as a finite number."""
    try:
        return value is not None and not pd.isna(value) and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def format_currency(value: Any, decimals: int = 1) -> str:
    """Format a dollar value using compact analyst-friendly units."""
    if not is_available(value):
        return "Not available"
    value = float(value)
    absolute = abs(value)
    if absolute >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:,.{decimals}f}T"
    if absolute >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.{decimals}f}B"
    if absolute >= 1_000_000:
        return f"${value / 1_000_000:,.{decimals}f}M"
    return f"${value:,.0f}"


def format_percent(value: Any, decimals: int = 1) -> str:
    """Format a decimal ratio as a percentage."""
    if not is_available(value):
        return "Not available"
    return f"{float(value) * 100:.{decimals}f}%"


def format_ratio(value: Any, decimals: int = 2) -> str:
    """Format a numeric ratio."""
    if not is_available(value):
        return "Not available"
    return f"{float(value):.{decimals}f}x"


def clean_for_json(value: Any) -> Any:
    """Convert pandas and NumPy values into JSON-safe Python values."""
    if isinstance(value, dict):
        return {key: clean_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_for_json(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if pd.isna(value):
        return None
    return value
