"""Planner node: The first agentic decision point.

Given a ticker, the LLM decides what matters for this company - a banks KPIs differ from
chipmaker's. Returns a typed research plan ( structured output), never free text.
Per 12 Factor Agents - LLM emits a payload
"""

from finsight.llm import generate_structured
from finsight.schemas.models import ResearchPlan

_PLANNER_PROMPT = """You are planning equity research for ticker {ticker}.
Decide what matters for THIS specific company and sector.
Pick metrics a real analyst would check for this kind of business
(a bank's KPIs are not a software company's), and news search terms
likely to surface material developments."""


def make_plan(ticker: str) -> ResearchPlan:
    return generate_structured(
        model="gemini-2.5-flash-lite",
        prompt=_PLANNER_PROMPT.format(ticker=ticker),
        schema=ResearchPlan,
    )
