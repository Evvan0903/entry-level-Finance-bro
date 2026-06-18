"""Small SEC EDGAR API client with disk caching."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from src.utils import CACHE_DIR, ensure_directories


SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "SEC Financial Report Agent contact@example.com")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class SECClientError(RuntimeError):
    """Raised when SEC data cannot be retrieved or interpreted."""


class SECClient:
    """Retrieve official SEC JSON endpoints while respecting fair access."""

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        cache_ttl_seconds: int = 24 * 60 * 60,
        timeout_seconds: int = 30,
    ) -> None:
        ensure_directories()
        self.cache_dir = Path(cache_dir)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": SEC_USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
                "Host": "data.sec.gov",
            }
        )
        self._last_request_at = 0.0

    def _cache_path(self, cache_key: str) -> Path:
        safe_key = "".join(character for character in cache_key if character.isalnum() or character in "-_")
        return self.cache_dir / f"{safe_key}.json"

    def _read_cache(self, cache_key: str) -> dict[str, Any] | None:
        path = self._cache_path(cache_key)
        if not path.exists() or time.time() - path.stat().st_mtime > self.cache_ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, cache_key: str, payload: dict[str, Any]) -> None:
        self._cache_path(cache_key).write_text(json.dumps(payload), encoding="utf-8")

    def get_json(self, url: str, cache_key: str) -> dict[str, Any]:
        """Get a JSON document from SEC, preferring a fresh disk cache."""
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        elapsed = time.monotonic() - self._last_request_at
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)

        headers = {"User-Agent": SEC_USER_AGENT}
        if "www.sec.gov" in url:
            headers["Host"] = "www.sec.gov"
        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout_seconds)
            self._last_request_at = time.monotonic()
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            stale_path = self._cache_path(cache_key)
            if stale_path.exists():
                try:
                    return json.loads(stale_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            raise SECClientError(f"SEC request failed for {url}: {exc}") from exc

        self._write_cache(cache_key, payload)
        return payload

    def get_ticker_mapping(self) -> dict[str, dict[str, Any]]:
        """Return SEC ticker records keyed by uppercase ticker."""
        raw = self.get_json(TICKERS_URL, "company_tickers")
        return {record["ticker"].upper(): record for record in raw.values()}

    def ticker_to_company(self, ticker: str) -> dict[str, Any]:
        """Map a ticker to its SEC company name and zero-padded CIK."""
        ticker = ticker.strip().upper()
        record = self.get_ticker_mapping().get(ticker)
        if not record:
            raise SECClientError(f"Ticker '{ticker}' was not found in the SEC ticker mapping.")
        return {
            "ticker": ticker,
            "name": record["title"],
            "cik": str(record["cik_str"]).zfill(10),
        }

    def get_submissions(self, cik: str) -> dict[str, Any]:
        """Return the SEC submissions document for a company."""
        return self.get_json(SUBMISSIONS_URL.format(cik=cik), f"submissions_{cik}")

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        """Return the SEC XBRL companyfacts document for a company."""
        return self.get_json(COMPANYFACTS_URL.format(cik=cik), f"companyfacts_{cik}")

    @staticmethod
    def latest_10k(submissions: dict[str, Any]) -> dict[str, str]:
        """Find the latest 10-K in a submissions response."""
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        for index, form in enumerate(forms):
            if form == "10-K":
                accession = recent["accessionNumber"][index]
                primary_document = recent["primaryDocument"][index]
                cik_no_zeros = str(int(submissions["cik"]))
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/"
                    f"{accession.replace('-', '')}/{primary_document}"
                )
                return {
                    "form": form,
                    "filing_date": recent["filingDate"][index],
                    "report_date": recent["reportDate"][index],
                    "accession_number": accession,
                    "primary_document": primary_document,
                    "filing_url": filing_url,
                }
        raise SECClientError("No recent 10-K filing was found for this company.")
