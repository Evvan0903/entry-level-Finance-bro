"""Extract normalized annual metrics from SEC companyfacts XBRL JSON."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


METRIC_TAGS = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "short_term_debt": ["ShortTermBorrowings", "ShortTermDebtCurrent", "LongTermDebtCurrent"],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
}


def _annual_usd_facts(company_facts: dict[str, Any], tags: list[str]) -> list[dict[str, Any]]:
    """Collect annual USD facts across fallback tags, preserving tag priority."""
    us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
    rows: list[dict[str, Any]] = []
    for priority, tag in enumerate(tags):
        units = us_gaap.get(tag, {}).get("units", {})
        for fact in units.get("USD", []):
            if fact.get("form") != "10-K" or fact.get("fp") != "FY" or fact.get("fy") is None:
                continue
            rows.append(
                {
                    "fy": int(fact["fy"]),
                    "value": fact.get("val"),
                    "filed": fact.get("filed", ""),
                    "end": fact.get("end", ""),
                    "tag_priority": priority,
                    "tag": tag,
                }
            )
    return rows


def extract_metric_series(company_facts: dict[str, Any], tags: list[str]) -> pd.Series:
    """Return one normalized annual metric series indexed by fiscal year."""
    rows = _annual_usd_facts(company_facts, tags)
    if not rows:
        return pd.Series(dtype="float64")

    facts = pd.DataFrame(rows)
    facts["value"] = pd.to_numeric(facts["value"], errors="coerce")
    facts = facts.dropna(subset=["value"])
    # Prefer the latest filed comparative/restated value, then the highest-priority tag.
    facts = facts.sort_values(["fy", "filed", "tag_priority"], ascending=[True, True, False])
    selected = facts.groupby("fy", as_index=False).tail(1)
    return selected.set_index("fy")["value"].sort_index().astype(float)


def extract_financial_metrics(company_facts: dict[str, Any], years: int = 5) -> pd.DataFrame:
    """Extract the latest annual 10-K metrics into a fiscal-year dataframe."""
    series_by_metric = {
        metric: extract_metric_series(company_facts, tags) for metric, tags in METRIC_TAGS.items()
    }
    available_series = [series for series in series_by_metric.values() if not series.empty]
    if not available_series:
        return pd.DataFrame(columns=list(METRIC_TAGS))

    all_years = sorted(set().union(*(series.index for series in available_series)))[-years:]
    frame = pd.DataFrame(index=pd.Index(all_years, name="fiscal_year"))
    for metric, series in series_by_metric.items():
        frame[metric] = series.reindex(frame.index)
    return frame.replace([np.inf, -np.inf], np.nan).sort_index()
