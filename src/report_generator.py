"""Render a downloadable HTML financial report."""

from __future__ import annotations

from typing import Any

from jinja2 import Template
import pandas as pd
import plotly.graph_objects as go

from src.utils import format_currency, format_percent, format_ratio


REPORT_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ company.name }} SEC Financial Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; color: #172033; background: #f5f7fb; }
    main { max-width: 1120px; margin: 0 auto; padding: 32px 22px 60px; }
    h1, h2 { color: #102a56; } h1 { margin-bottom: 4px; }
    .muted { color: #64748b; } .card { background: white; border: 1px solid #e2e8f0;
      border-radius: 12px; padding: 20px; margin: 18px 0; box-shadow: 0 2px 8px #0f172a10; }
    .overview, .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
    .item { background: #f8fafc; padding: 12px; border-radius: 8px; }
    .label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: .04em; }
    .value { font-weight: 700; margin-top: 5px; } a { color: #2563eb; }
    .disclaimer { font-size: 13px; color: #64748b; }
  </style>
</head>
<body><main>
  <h1>SEC Financial Report Agent</h1>
  <div class="muted">{{ company.name }} ({{ company.ticker }}) | Generated from SEC EDGAR data</div>
  <section class="card"><h2>Company Overview</h2><div class="overview">
    {% for label, value in overview_items %}<div class="item"><div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div></div>{% endfor %}
  </div><p><a href="{{ company.filing_url }}">View latest 10-K filing</a></p></section>
  <section class="card"><h2>KPI Summary</h2><div class="kpis">
    {% for label, value in kpi_items %}<div class="item"><div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div></div>{% endfor %}
  </div></section>
  {% for chart in charts %}<section class="card">{{ chart }}</section>{% endfor %}
  <section class="card"><h2>Analyst Summary</h2>
    {% for title, text in summary.items() %}<h3>{{ title }}</h3><p>{{ text }}</p>{% endfor %}
  </section>
  <section class="card"><h2>Source Links and Disclaimer</h2>
    <p><a href="{{ company.filing_url }}">{{ company.filing_url }}</a></p>
    <p class="disclaimer">{{ disclaimer }}</p>
  </section>
</main></body></html>"""
)

DASHBOARD_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ company.name }} Financial Dashboard</title>
  <style>
    :root { --blue: #2563eb; --ink: #14213d; --muted: #64748b; --line: #e2e8f0; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Inter, Arial, sans-serif; color: var(--ink);
      background: linear-gradient(135deg, #eef5ff 0%, #f8fafc 45%, #edfdf8 100%); }
    main { max-width: 1280px; margin: 0 auto; padding: 34px 24px 56px; }
    .hero { background: #0f1f3d; color: white; border-radius: 22px; padding: 30px;
      box-shadow: 0 20px 48px #0f172a25; }
    .hero h1 { margin: 0 0 8px; font-size: 34px; }
    .hero p { margin: 0; color: #cbd5e1; }
    .meta { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 20px; }
    .pill { background: #ffffff14; border: 1px solid #ffffff26; border-radius: 999px; padding: 9px 14px; }
    .kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 22px 0; }
    .kpi, .panel, .summary { background: #fffffff2; border: 1px solid var(--line); border-radius: 18px;
      padding: 18px; box-shadow: 0 12px 28px #0f172a12; }
    .label { color: var(--muted); font-size: 12px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
    .value { font-size: 25px; font-weight: 800; margin-top: 8px; }
    .charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .wide { grid-column: 1 / -1; }
    h2 { margin: 0 0 14px; font-size: 19px; }
    h3 { margin-bottom: 6px; color: #1e3a8a; }
    a { color: #bfdbfe; }
    .summary { margin-top: 18px; }
    .footer { margin-top: 18px; color: var(--muted); font-size: 13px; }
    @media (max-width: 920px) { .kpis, .charts { grid-template-columns: 1fr; } .wide { grid-column: auto; } }
  </style>
</head>
<body><main>
  <section class="hero">
    <h1>{{ company.name }} Financial Dashboard</h1>
    <p>SEC Financial Report Agent | Latest annual 10-K data from SEC EDGAR</p>
    <div class="meta">
      <div class="pill">Ticker: {{ company.ticker }}</div>
      <div class="pill">CIK: {{ company.cik }}</div>
      <div class="pill">Filing: {{ company.form }}</div>
      <div class="pill">Report date: {{ company.report_date }}</div>
      <div class="pill"><a href="{{ company.filing_url }}">Open SEC filing</a></div>
    </div>
  </section>
  <section class="kpis">
    {% for label, value in kpi_items %}<div class="kpi"><div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div></div>{% endfor %}
  </section>
  <section class="charts">
    {% for chart in charts %}<div class="panel{% if loop.index == 3 %} wide{% endif %}">{{ chart }}</div>{% endfor %}
  </section>
  <section class="summary">
    <h2>Analyst Summary</h2>
    {% for title, text in summary.items() %}<h3>{{ title }}</h3><p>{{ text }}</p>{% endfor %}
  </section>
  <p class="footer">{{ disclaimer }}</p>
</main></body></html>"""
)


def generate_html_report(
    company: dict[str, Any],
    metrics: pd.DataFrame,
    charts: dict[str, go.Figure],
    summary: dict[str, str],
) -> str:
    """Build a self-contained HTML report with embedded Plotly charts."""
    latest = metrics.iloc[-1] if not metrics.empty else pd.Series(dtype=float)
    chart_html = []
    for index, figure in enumerate(charts.values()):
        chart_html.append(
            figure.to_html(full_html=False, include_plotlyjs=True if index == 0 else False)
        )

    overview_items = [
        ("Company Name", company.get("name", "Not available")),
        ("Ticker", company.get("ticker", "Not available")),
        ("CIK", company.get("cik", "Not available")),
        ("Latest Filing", company.get("form", "Not available")),
        ("Filing Date", company.get("filing_date", "Not available")),
        ("Report Date", company.get("report_date", "Not available")),
    ]
    kpi_items = [
        ("Revenue", format_currency(latest.get("revenue"))),
        ("Net Income", format_currency(latest.get("net_income"))),
        ("Net Margin", format_percent(latest.get("net_margin"))),
        ("Cash", format_currency(latest.get("cash"))),
        ("Total Debt", format_currency(latest.get("total_debt"))),
        ("Current Ratio", format_ratio(latest.get("current_ratio"))),
        ("Debt-to-Assets", format_percent(latest.get("debt_to_assets"))),
        ("Operating Cash Flow", format_currency(latest.get("operating_cash_flow"))),
    ]
    return REPORT_TEMPLATE.render(
        company=company,
        overview_items=overview_items,
        kpi_items=kpi_items,
        charts=chart_html,
        summary=summary,
        disclaimer=(
            "This report is generated from SEC filings for educational and analytical purposes only. "
            "It is not investment advice."
        ),
    )


def generate_dashboard_html(
    company: dict[str, Any],
    metrics: pd.DataFrame,
    charts: dict[str, go.Figure],
    summary: dict[str, str],
) -> str:
    """Build a dashboard-first HTML sample with KPI cards and chart panels."""
    latest = metrics.iloc[-1] if not metrics.empty else pd.Series(dtype=float)
    chart_html = [
        figure.to_html(full_html=False, include_plotlyjs=True if index == 0 else False)
        for index, figure in enumerate(charts.values())
    ]
    kpi_items = [
        ("Revenue", format_currency(latest.get("revenue"))),
        ("Net Income", format_currency(latest.get("net_income"))),
        ("Net Margin", format_percent(latest.get("net_margin"))),
        ("Operating Cash Flow", format_currency(latest.get("operating_cash_flow"))),
        ("Cash", format_currency(latest.get("cash"))),
        ("Total Debt", format_currency(latest.get("total_debt"))),
        ("Current Ratio", format_ratio(latest.get("current_ratio"))),
        ("Debt-to-Assets", format_percent(latest.get("debt_to_assets"))),
    ]
    return DASHBOARD_TEMPLATE.render(
        company=company,
        kpi_items=kpi_items,
        charts=chart_html,
        summary=summary,
        disclaimer=(
            "This report is generated from SEC filings for educational and analytical purposes only. "
            "It is not investment advice."
        ),
    )
