"""Generate AAPL sample dashboard and report artifacts without launching Streamlit."""

from pathlib import Path

from app import build_report
from src.report_generator import generate_dashboard_html
from src.utils import OUTPUTS_DIR, ensure_directories


def main() -> None:
    """Generate and save AAPL dashboard, report, and supporting metrics."""
    ensure_directories()
    result = build_report("AAPL")
    report_path = Path(OUTPUTS_DIR) / "AAPL_SEC_financial_report.html"
    report_path.write_text(result["html_report"], encoding="utf-8")
    dashboard_path = Path(OUTPUTS_DIR) / "AAPL_dashboard.html"
    dashboard_html = generate_dashboard_html(
        result["company"],
        result["metrics"],
        result["charts"],
        result["summary"],
    )
    dashboard_path.write_text(dashboard_html, encoding="utf-8")
    metrics_path = Path(OUTPUTS_DIR) / "AAPL_annual_metrics.csv"
    result["metrics"].to_csv(metrics_path)
    print(f"Generated {dashboard_path}")
    print(f"Generated {report_path}")
    print(f"Generated {metrics_path}")


if __name__ == "__main__":
    main()
