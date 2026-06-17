"""Planner node: The first agentic decision point.

Given a ticker, the LLM decides what matters for this company - a banks KPIs differ from
chipmaker's. Returns a typed research plan ( structured output), never free text.
Per 12 Factor Agents - LLM emits a payload
"""

import os

from dotenv import load_dotenv
from google import genai

from finsight.schemas.models import ResearchPlan

_PLANNER_PROMPT = """You are planning equity research for ticker {ticker}.
Decide what matters for THIS specific company and sector.
Pick metrics a real analyst would check for this kind of business
(a bank's KPIs are not a software company's), and news search terms
likely to surface material developments."""


def make_plan(ticker: str) -> ResearchPlan:
    load_dotenv()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=_PLANNER_PROMPT.format(ticker=ticker),
        config={
            "response_mime_type": "application/json",
            "response_schema": ResearchPlan,
        },
    )

    plan = response.parsed
    if not isinstance(plan, ResearchPlan):
        raise ValueError(f"planner returned unparseable  plan for {ticker} : {type(plan)}")
    return plan
