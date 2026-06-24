"""Typed data contracts for FinSightAI.
These models are the spine of the system.
Every LLM call must emit data that validates against them, and the grounding contract
- no claim without evidence
- is enforced here in the type system, not just in prompts
"""

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["market", "fundamentals", "news", "filing", "sentiment"]


class Evidence(BaseModel):
    id: str
    source_type: SourceType
    title: str
    url: str | None = None
    published_at: str | None = None
    content: str
    meta: dict[str, str] = Field(default_factory=dict)


class MemoSection(BaseModel):
    heading: str
    body_md: str
    evidence_ids: list[str]


class Snapshot(BaseModel):
    price: str = ""
    market_cap: str = ""
    pe_ratio: str = ""
    fifty_two_week_high: str = ""
    fifty_two_week_low: str = ""
    sector: str = ""


class InvestmentMemo(BaseModel):
    ticker: str
    company: str
    as_of: str
    snapshot: Snapshot = Field(default_factory=Snapshot)
    thesis: MemoSection
    opportunities: list[MemoSection] = Field(default_factory=list)
    risks: list[MemoSection] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    disclaimer: str


class ResearchPlan(BaseModel):
    company_name: str
    sector: str
    is_us_listed: bool
    key_metrics_to_check: list[str]
    news_search_terms: list[str]


class ExtractedInsights(BaseModel):
    """One risk or theme distiled from filing section"""

    label: str  # short name, e.g. "Supply chain concentration"
    summary: str  # One sentence in plain english
    evidence_id: str  # which filing Evidence this came from


class FilingInsights(BaseModel):
    """What extraction node returns for every filings"""

    risks: list[ExtractedInsights]
    themes: list[ExtractedInsights]
