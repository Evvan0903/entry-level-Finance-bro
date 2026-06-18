"""Generate analyst-style commentary with an optional OpenAI enhancement."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from src.utils import clean_for_json, format_currency, format_percent, format_ratio, is_available


SECTION_NAMES = [
    "Executive Summary",
    "Financial Performance",
    "Profitability and Margin",
    "Balance Sheet and Liquidity",
    "Cash Flow Quality",
    "Watch Points",
]


def _change_phrase(value: Any, positive: str, negative: str) -> str:
    if not is_available(value):
        return "The year-over-year change is not available."
    direction = positive if float(value) >= 0 else negative
    return f"It {direction} {abs(float(value)) * 100:.1f}% year over year."


def rule_based_summary(metrics: pd.DataFrame) -> dict[str, str]:
    """Create a concise summary using only calculated structured metrics."""
    if metrics.empty:
        return {section: "Not available." for section in SECTION_NAMES}

    latest = metrics.iloc[-1]
    prior = metrics.iloc[-2] if len(metrics) > 1 else None
    year = int(metrics.index[-1])
    revenue_growth = latest.get("revenue_growth")
    net_income_change = (
        latest.get("net_income") / prior.get("net_income") - 1
        if prior is not None
        and is_available(latest.get("net_income"))
        and is_available(prior.get("net_income"))
        and float(prior.get("net_income")) != 0
        else None
    )

    executive = (
        f"For fiscal {year}, the company reported revenue of {format_currency(latest.get('revenue'))} "
        f"and net income of {format_currency(latest.get('net_income'))}. "
        f"Net margin was {format_percent(latest.get('net_margin'))}, while operating cash flow was "
        f"{format_currency(latest.get('operating_cash_flow'))}."
    )
    performance = (
        f"Revenue was {format_currency(latest.get('revenue'))}. "
        f"{_change_phrase(revenue_growth, 'increased', 'decreased')} "
        f"Net income was {format_currency(latest.get('net_income'))}. "
        f"{_change_phrase(net_income_change, 'increased', 'decreased')}"
    )
    profitability = (
        f"Gross margin was {format_percent(latest.get('gross_margin'))}, operating margin was "
        f"{format_percent(latest.get('operating_margin'))}, and net margin was "
        f"{format_percent(latest.get('net_margin'))}."
    )
    liquidity = (
        f"Cash was {format_currency(latest.get('cash'))} versus total debt of "
        f"{format_currency(latest.get('total_debt'))}. The current ratio was "
        f"{format_ratio(latest.get('current_ratio'))}, and debt-to-assets was "
        f"{format_percent(latest.get('debt_to_assets'))}."
    )
    cash_flow = (
        f"Operating cash flow was {format_currency(latest.get('operating_cash_flow'))}, compared with "
        f"net income of {format_currency(latest.get('net_income'))}. Estimated free cash flow was "
        f"{format_currency(latest.get('free_cash_flow'))}, and operating cash flow margin was "
        f"{format_percent(latest.get('ocf_margin'))}."
    )

    watch_points = []
    if is_available(revenue_growth) and revenue_growth < 0:
        watch_points.append("Revenue contracted in the latest fiscal year.")
    if is_available(latest.get("current_ratio")) and latest.get("current_ratio") < 1:
        watch_points.append("The current ratio is below 1.0x, indicating limited short-term coverage.")
    if is_available(latest.get("net_debt")) and latest.get("net_debt") > 0:
        watch_points.append("Total debt exceeds cash.")
    if is_available(latest.get("operating_cash_flow")) and is_available(latest.get("net_income")):
        if latest.get("operating_cash_flow") < latest.get("net_income"):
            watch_points.append("Operating cash flow trails reported net income.")
    if not watch_points:
        watch_points.append("Monitor revenue growth, margin durability, leverage, and cash conversion.")

    return {
        "Executive Summary": executive,
        "Financial Performance": performance,
        "Profitability and Margin": profitability,
        "Balance Sheet and Liquidity": liquidity,
        "Cash Flow Quality": cash_flow,
        "Watch Points": " ".join(watch_points),
    }


def generate_summary(metrics: pd.DataFrame, company_overview: dict[str, Any]) -> tuple[dict[str, str], str]:
    """Use OpenAI when configured, otherwise return a reliable rule-based summary."""
    fallback = rule_based_summary(metrics)
    if not os.getenv("OPENAI_API_KEY"):
        return fallback, "Rule-based summary"

    prompt = (
        "You are a financial analyst assistant. Using only the provided structured financial metrics, "
        "write a concise financial analysis report. Do not invent numbers. If a metric is missing, say "
        "it is not available. Do not provide buy/sell/hold recommendations. Focus on revenue trend, "
        "profitability, liquidity, cash flow quality, and watch points. Return valid JSON with exactly "
        f"these keys: {SECTION_NAMES}.\n\nCompany: {json.dumps(company_overview)}\n"
        f"Metrics: {json.dumps(clean_for_json(metrics.reset_index().to_dict(orient='records')))}"
    )
    try:
        from openai import OpenAI

        response = OpenAI().responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
        return {section: str(parsed.get(section, fallback[section])) for section in SECTION_NAMES}, "OpenAI summary"
    except Exception:
        return fallback, "Rule-based summary (OpenAI unavailable)"
