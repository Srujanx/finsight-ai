"""Fetch SEC 10-K Risk Factors (Item 1A) + MD&A (Item 7) as Evidence.

Bible §4.1: parse ONLY these two sections. Full-filing parsing is a tar pit.
Foreign filers (20-F) and missing filings degrade gracefully — no crash.
"""

import os

from edgar import Company, set_identity

from finsight.schemas.models import Evidence

# Cap section text so we don't blow the synthesis token budget (bible §5.2).
_MAX_SECTION_CHARS = 6000


def _chunk_section(text: str, max_chars: int = _MAX_SECTION_CHARS) -> str:
    """Trim a filing section to a token-budget-friendly size."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[truncated]"


def fetch_filing_evidence(ticker: str) -> list[Evidence]:
    """Return Evidence for Risk Factors and MD&A from the latest 10-K.

    Returns an empty list (never raises) if no 10-K is found — e.g. foreign
    filers (20-F) or companies with no recent filing.
    """
    set_identity(os.environ["EDGAR_USER_AGENT"])
    evidence: list[Evidence] = []

    company = Company(ticker)
    filings = company.get_filings(form="10-K")
    latest = filings.latest() if filings else None
    if latest is None:
        return evidence  # no 10-K (foreign filer, new listing, etc.)

    tenk = latest.obj()  # type: ignore[attr-defined]
    filing_date = str(latest.filing_date)  # type: ignore[attr-defined]

    # NOTE: confirm these attribute names against your scratch exploration (8A).
    risk_text = getattr(tenk, "risk_factors", None)
    if risk_text:
        evidence.append(
            Evidence(
                id="10k_risk",
                source_type="filing",
                title=f"{ticker} 10-K Risk Factors (filed {filing_date})",
                content=_chunk_section(risk_text),
                meta={"form": "10-K", "section": "Item 1A", "filed": filing_date},
            )
        )

    mdna_text = getattr(tenk, "management_discussion", None)
    if mdna_text:
        evidence.append(
            Evidence(
                id="10k_mdna",
                source_type="filing",
                title=f"{ticker} 10-K MD&A (filed {filing_date})",
                content=_chunk_section(mdna_text),
                meta={"form": "10-K", "section": "Item 7", "filed": filing_date},
            )
        )

    return evidence
