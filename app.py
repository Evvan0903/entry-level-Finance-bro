"""Streamlit entry point for the SEC Financial Report Agent."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.chart_generator import generate_charts
from src.llm_summary import generate_summary
from src.metrics_calculator import calculate_metrics, latest_kpis
from src.report_generator import generate_html_report
from src.sec_client import SECClient, SECClientError
from src.utils import (
    REPORTS_DIR,
    ensure_directories,
    format_currency,
    format_percent,
    format_ratio,
)
from src.xbrl_mapper import extract_financial_metrics


DISCLAIMER = (
    "This report is generated from SEC filings for educational and analytical purposes only. "
    "It is not investment advice."
)


def escape_streamlit_markdown(text: str) -> str:
    """Keep currency symbols from being interpreted as inline math."""
    return text.replace("$", r"\$")


def is_generic_template_warning(submissions: dict) -> bool:
    """Identify companies likely to need industry-specific financial metrics."""
    sic = str(submissions.get("sic", ""))
    description = str(submissions.get("sicDescription", "")).lower()
    keywords = ("bank", "insurance", "reit", "real estate investment trust")
    return sic.startswith("6") or any(keyword in description for keyword in keywords)


def build_report(ticker: str) -> dict:
    """Run the complete SEC retrieval and report-generation pipeline."""
    client = SECClient()
    company = client.ticker_to_company(ticker)
    submissions = client.get_submissions(company["cik"])
    filing = client.latest_10k(submissions)
    company.update(filing)
    company["sic"] = submissions.get("sic", "Not available")
    company["sic_description"] = submissions.get("sicDescription", "Not available")

    company_facts = client.get_company_facts(company["cik"])
    financials = extract_financial_metrics(company_facts)
    if financials.empty:
        raise SECClientError("No usable annual 10-K XBRL facts were found for this company.")

    metrics = calculate_metrics(financials)
    charts = generate_charts(metrics)
    summary, summary_source = generate_summary(metrics, company)
    html_report = generate_html_report(company, metrics, charts, summary)
    return {
        "company": company,
        "metrics": metrics,
        "charts": charts,
        "summary": summary,
        "summary_source": summary_source,
        "html_report": html_report,
        "show_industry_warning": is_generic_template_warning(submissions),
    }


def display_overview(company: dict) -> None:
    """Display filing and company metadata."""
    st.header("1. Company Overview")
    left, right = st.columns(2)
    with left:
        st.write(f"**Company name:** {company['name']}")
        st.write(f"**Ticker:** {company['ticker']}")
        st.write(f"**CIK:** {company['cik']}")
        st.write(f"**Industry:** {company['sic_description']}")
    with right:
        st.write(f"**Latest filing type:** {company['form']}")
        st.write(f"**Filing date:** {company['filing_date']}")
        st.write(f"**Report date:** {company['report_date']}")
        st.link_button("Open SEC filing", company["filing_url"])


def display_kpis(metrics: pd.DataFrame) -> None:
    """Display the latest annual KPI cards."""
    st.header("2. KPI Summary")
    kpis = latest_kpis(metrics)
    first_row = st.columns(4)
    first_row[0].metric("Revenue", format_currency(kpis.get("revenue")))
    first_row[1].metric("Net Income", format_currency(kpis.get("net_income")))
    first_row[2].metric("Net Margin", format_percent(kpis.get("net_margin")))
    first_row[3].metric("Cash", format_currency(kpis.get("cash")))
    second_row = st.columns(4)
    second_row[0].metric("Total Debt", format_currency(kpis.get("total_debt")))
    second_row[1].metric("Current Ratio", format_ratio(kpis.get("current_ratio")))
    second_row[2].metric("Debt-to-Assets", format_percent(kpis.get("debt_to_assets")))
    second_row[3].metric("Operating Cash Flow", format_currency(kpis.get("operating_cash_flow")))


def display_report(result: dict) -> None:
    """Render a completed report in Streamlit."""
    company = result["company"]
    metrics = result["metrics"]
    charts = result["charts"]

    if result["show_industry_warning"]:
        st.warning(
            "This MVP uses a generic non-financial-company template. Banks, insurers, and REITs "
            "may require customized metrics."
        )
    display_overview(company)
    display_kpis(metrics)

    st.header("3. Financial Performance")
    left, right = st.columns(2)
    left.plotly_chart(charts["revenue"], width="stretch")
    right.plotly_chart(charts["net_income"], width="stretch")

    st.header("4. Profitability & Margin")
    st.plotly_chart(charts["margins"], width="stretch")

    st.header("5. Balance Sheet & Liquidity")
    st.plotly_chart(charts["cash_debt"], width="stretch")
    st.info(escape_streamlit_markdown(result["summary"]["Balance Sheet and Liquidity"]))

    st.header("6. Cash Flow Quality")
    st.plotly_chart(charts["cash_flow"], width="stretch")

    st.header("7. AI Analyst Summary")
    st.caption(result["summary_source"])
    for section, text in result["summary"].items():
        st.subheader(section)
        st.markdown(escape_streamlit_markdown(text))

    with st.expander("View annual financial data"):
        st.dataframe(metrics.sort_index(ascending=False), width="stretch")

    st.header("8. Source Links and Disclaimer")
    st.markdown(f"[Latest 10-K filing]({company['filing_url']})")
    st.caption(DISCLAIMER)
    file_name = f"{company['ticker']}_SEC_financial_report.html"
    st.download_button(
        "Download HTML Report",
        data=result["html_report"],
        file_name=file_name,
        mime="text/html",
        type="primary",
    )


def main() -> None:
    """Configure and run the Streamlit application."""
    load_dotenv()
    ensure_directories()
    st.set_page_config(page_title="SEC Financial Report ", page_icon="📊", layout="wide")
    st.title("SEC Financial Report")
    st.write("Generate an annual financial analysis report from official SEC EDGAR data.")

    with st.form("ticker_form"):
        ticker = st.text_input("Public company ticker", value="CVX", max_chars=12).strip().upper()
        submitted = st.form_submit_button("Generate Report", type="primary")

    if submitted:
        if not ticker:
            st.error("Enter a ticker before generating a report.")
            return
        try:
            with st.spinner(f"Retrieving SEC data and analyzing {ticker}..."):
                result = build_report(ticker)
                report_path = REPORTS_DIR / f"{ticker}_SEC_financial_report.html"
                report_path.write_text(result["html_report"], encoding="utf-8")
                st.session_state["report_result"] = result
        except SECClientError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error(f"Unable to generate the report: {exc}")
            return

    if "report_result" in st.session_state:
        display_report(st.session_state["report_result"])


if __name__ == "__main__":
    main()
