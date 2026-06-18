"""Generate the five Plotly charts used by the app and HTML report."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


COLORS = {
    "revenue": "#2563EB",
    "net_income": "#16A34A",
    "gross_margin": "#7C3AED",
    "operating_margin": "#EA580C",
    "net_margin": "#16A34A",
    "cash": "#0891B2",
    "total_debt": "#DC2626",
    "operating_cash_flow": "#0284C7",
}


def _base_figure(title: str, y_title: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=390,
        margin=dict(l=30, r=20, t=65, b=35),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Fiscal Year",
        yaxis_title=y_title,
        hovermode="x unified",
    )
    return figure


def _add_line(figure: go.Figure, metrics: pd.DataFrame, column: str, label: str) -> None:
    if column in metrics and metrics[column].notna().any():
        figure.add_trace(
            go.Scatter(
                x=metrics.index.astype(str),
                y=metrics[column],
                name=label,
                mode="lines+markers",
                line=dict(color=COLORS.get(column), width=3),
            )
        )


def generate_charts(metrics: pd.DataFrame) -> dict[str, go.Figure]:
    """Create all required Plotly trend charts."""
    revenue = _base_figure("Revenue Trend", "USD")
    _add_line(revenue, metrics, "revenue", "Revenue")

    net_income = _base_figure("Net Income Trend", "USD")
    _add_line(net_income, metrics, "net_income", "Net Income")

    margins = _base_figure("Margin Trend", "Margin")
    for column, label in (
        ("gross_margin", "Gross Margin"),
        ("operating_margin", "Operating Margin"),
        ("net_margin", "Net Margin"),
    ):
        _add_line(margins, metrics, column, label)
    margins.update_yaxes(tickformat=".1%")

    cash_debt = _base_figure("Cash vs Debt Trend", "USD")
    _add_line(cash_debt, metrics, "cash", "Cash")
    _add_line(cash_debt, metrics, "total_debt", "Total Debt")

    cash_flow = _base_figure("Operating Cash Flow vs Net Income", "USD")
    _add_line(cash_flow, metrics, "operating_cash_flow", "Operating Cash Flow")
    _add_line(cash_flow, metrics, "net_income", "Net Income")

    return {
        "revenue": revenue,
        "net_income": net_income,
        "margins": margins,
        "cash_debt": cash_debt,
        "cash_flow": cash_flow,
    }
