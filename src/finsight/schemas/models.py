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
    """One unit of gathered information.
    Everything the agent learns: A news article, a 10-k risk paragraph, a price snapshot
    becomes one of these, with a stable id that memo sections cite.
    """

    id: str = Field(min_length=1)  # Example: "news_03" , "10k_risk_02"
    source_type: SourceType  # Linteral = the LLM cant invent new types
    title: str = Field(min_length=1)
    url: str | None = None
    published_at: str | None = None  # ISO-8601 string: keep it simple for now
    content: str = Field(min_length=1, max_length=8_000)
    meta: dict = Field(default_factory=dict)  # never '= {}'


class MemoSection(BaseModel):
    # A block of the memo. The grounding contract lives in the evidence_ids
    heading: str = Field(min_length=1)
    body_md: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)  # empty list = invalid section. The contract


class InvestmentMemo(BaseModel):
    # The final product of a research
    ticker: str = Field(min_length=1, max_length=10)
    company: str = Field(min_length=1)
    as_of: str
    snapshot: dict = Field(default_factory=dict)  # price, mcap, P/E, margins
    thesis: MemoSection
    opportunities: list[MemoSection] = Field(default_factory=list)
    risks: list[MemoSection] = Field(default_factory=list)
    sentiment: dict = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
    disclaimer: str = Field(min_length=1)


class ResearchPlan(BaseModel):
    # What the planner decides on a gicen ticker. LLM emits this shape

    company_name: str = Field(min_length=1)
    sector: str = Field(min_length=1)
    is_us_listed: bool
    key_metrics_to_check: list[str] = Field(min_length=1)  # sector-specific KPIs
    news_search_terms: list[str] = Field(min_length=1)
