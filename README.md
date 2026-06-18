# SEC Financial Report Agent

SEC Financial Report Agent is a Python and Streamlit MVP that turns a public-company ticker into an automated annual financial analysis report. It uses official SEC EDGAR JSON APIs, normalizes XBRL facts, calculates common financial metrics, creates interactive charts, writes an analyst-style summary, and exports a downloadable HTML report.

## Why This Project Matters

Financial analysis often requires repetitive work: locating filings, reconciling XBRL tags, calculating ratios, building charts, and drafting commentary. This project demonstrates how finance-domain AI and data automation can turn structured regulatory data into a repeatable first-pass report while preserving source links and avoiding invented figures.

## Data Source

The app uses official SEC EDGAR APIs:

- Ticker-to-CIK mapping: `https://www.sec.gov/files/company_tickers.json`
- Company submissions: `https://data.sec.gov/submissions/CIK##########.json`
- Company facts/XBRL: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

Requests include a clear User-Agent and are cached locally in `data/cache/` to reduce repeated SEC calls.

## Features

- Maps ticker symbols to SEC CIK identifiers
- Finds the latest annual 10-K and links to the filing
- Extracts the latest 4-5 fiscal years of annual `us-gaap` XBRL facts
- Uses fallback XBRL tags and tolerates missing metrics
- Calculates financial ratios, growth metrics, debt, and free cash flow
- Creates five interactive Plotly charts
- Uses OpenAI for commentary when configured, with a rule-based fallback
- Displays a Streamlit dashboard and downloads a self-contained HTML report
- Warns when the generic template may not fit banks, insurers, or REITs

## Metrics Calculated

The app extracts revenue, gross profit, operating income, net income, cash, assets, liabilities, current assets, current liabilities, long-term debt, short-term debt, equity, operating cash flow, and capital expenditures.

It calculates:

- Total debt and net debt
- Free cash flow
- Revenue growth
- Gross, operating, and net margins
- Current ratio
- Debt-to-assets
- Operating cash flow margin

## Run Locally

```bash
cd Financial_project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Set `SEC_USER_AGENT` in `.env` to your name and contact email before making SEC requests. An OpenAI key is optional. Without `OPENAI_API_KEY`, the app automatically generates a rule-based analyst summary.

## Generate the AAPL Sample

```bash
python generate_sample_report.py
```

This creates:

- `outputs/AAPL_SEC_financial_report.html`
- `outputs/AAPL_annual_metrics.csv`

## Project Structure

```text
Financial_project/
├── app.py
├── generate_sample_report.py
├── requirements.txt
├── README.md
├── .env.example
├── src/
│   ├── sec_client.py
│   ├── xbrl_mapper.py
│   ├── metrics_calculator.py
│   ├── chart_generator.py
│   ├── report_generator.py
│   ├── llm_summary.py
│   └── utils.py
├── data/
│   ├── cache/
│   └── reports/
└── outputs/
```

## Limitations

- The MVP uses latest 10-K annual data only; it does not analyze 10-Q filings.
- Generic metrics work best for non-financial operating companies.
- Banks, insurers, REITs, and other specialized industries require tailored metrics.
- SEC XBRL tags and company reporting practices vary, so some fields may be unavailable.
- The generated analysis is educational and analytical, not investment advice.

## Future Improvements

- Add 10-Q quarterly analysis
- Add industry-specific KPI modules
- Add risk factor extraction from Item 1A
- Add MD&A text summarization
- Add PDF export
- Add database storage
- Add multi-company comparison
