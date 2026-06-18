"""Calculate ratios and growth metrics from normalized SEC facts."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _partial_sum(left: pd.Series, right: pd.Series) -> pd.Series:
    """Sum two series while leaving rows with both inputs missing as NaN."""
    result = left.fillna(0) + right.fillna(0)
    return result.mask(left.isna() & right.isna())


def calculate_metrics(financials: pd.DataFrame) -> pd.DataFrame:
    """Add debt, free cash flow, growth, margin, and liquidity calculations."""
    metrics = financials.copy()
    for column in (
        "long_term_debt",
        "short_term_debt",
        "cash",
        "operating_cash_flow",
        "capex",
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "current_assets",
        "current_liabilities",
        "assets",
    ):
        if column not in metrics:
            metrics[column] = np.nan

    metrics["total_debt"] = _partial_sum(metrics["long_term_debt"], metrics["short_term_debt"])
    metrics["net_debt"] = metrics["total_debt"] - metrics["cash"]
    metrics["free_cash_flow"] = metrics["operating_cash_flow"] - metrics["capex"].abs()
    metrics["revenue_growth"] = metrics["revenue"].pct_change(fill_method=None)
    metrics["gross_margin"] = metrics["gross_profit"] / metrics["revenue"]
    metrics["operating_margin"] = metrics["operating_income"] / metrics["revenue"]
    metrics["net_margin"] = metrics["net_income"] / metrics["revenue"]
    metrics["current_ratio"] = metrics["current_assets"] / metrics["current_liabilities"]
    metrics["debt_to_assets"] = metrics["total_debt"] / metrics["assets"]
    metrics["ocf_margin"] = metrics["operating_cash_flow"] / metrics["revenue"]
    return metrics.replace([np.inf, -np.inf], np.nan)


def latest_kpis(metrics: pd.DataFrame) -> dict[str, float]:
    """Return the latest fiscal year's KPI values."""
    if metrics.empty:
        return {}
    row = metrics.iloc[-1]
    return {"fiscal_year": int(metrics.index[-1]), **row.to_dict()}
