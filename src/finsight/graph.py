"""The LangGraph StateGraph: linear pipeline, same output

fetch_market -> fetch_news -> sythesize -> END
"""

import os
from datetime import date
from pathlib import Path

from google import genai
from langgraph.graph import END, START, StateGraph

from finsight.planner import make_plan
from finsight.schemas.models import Evidence, InvestmentMemo
from finsight.state import AgentState
from finsight.tracer import get_headlines, get_snapshot

_SYNTH_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "synthesize_memo_v1.md"


def planner_node(state: AgentState) -> dict:
    # First Agentic decision point: First define what matters for this company
    try:
        plan = make_plan(state["ticker"])
        return {"plan": plan}
    except Exception as exc:
        return {"errors": [f"planner failed: {exc}"]}


def fetch_market_node(state: AgentState) -> dict:
    # Returns Evidence to be appended.
    ticker = state["ticker"]
    try:
        snap = get_snapshot(ticker)
        ev = Evidence(
            id="px_snapshot",
            source_type="market",
            title=f"{snap.get('name', ticker)} market snapshot",
            content=str(snap),
            meta=snap,
        )
        return {"evidence": [ev]}
    except Exception as exc:
        return {"erros": [f"fetch_market failed: {exc}"]}


def fetch_news_node(state: AgentState) -> dict:
    # One evidence per headline.
    ticker = state["ticker"]
    try:
        headlines = get_headlines(ticker)
        evidence = [
            Evidence(
                id=f"news_{i:02d}",
                source_type="news",
                title=item["headline"],
                url=item.get("url"),
                content=item["headline"],
                meta={"source": item.get("source", "unknown")},
            )
            for i, item in enumerate(headlines, start=1)
        ]
        return {"evidence": evidence}
    except Exception as exc:
        return {"errors": [f"fetch_news failed: {exc}"]}


def _format_evidence(evidence: list[Evidence]) -> str:
    # Render evidence as a labelled block
    lines = []
    for ev in evidence:
        lines.append(f"[{ev.id}] ({ev.source_type}) {ev.title}\n{ev.content}\n")
    return "\n".join(lines)


def synthesize_node(state: AgentState) -> dict:
    # Reads evidence back out of state

    # Reconstructing the snapchat dict and headline list from evidence

    # Produce a validated InvestmentMemo, Structured output + grounded contracting
    evidence = state["evidence"]
    if not evidence:
        return {"errors": ["synthesis: no evidence to work with"]}

    snapshot: dict = {}
    # headlines: list[dict] = []
    for ev in state["evidence"]:
        if ev.source_type == "market":
            snapshot = ev.meta
        # elif ev.source_type == "news":
        #     headlines.append({"headline": ev.title, "source": ev.meta.get("source", "")})

    prompt = _SYNTH_PROMPT.read_text().format(
        ticker=state["ticker"],
        evidence=_format_evidence(evidence),
    )

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": InvestmentMemo,
            },
        )
        memo = response.parsed
        if not isinstance(memo, InvestmentMemo):
            return {"error": [f"synthesize: unparsable memo ({type(memo)})"]}
        # Force field the model shouldn't invest
        memo.ticker = state["ticker"]
        memo.as_of = date.today().isoformat()
        memo.snapshot = snapshot or memo.snapshot
        return {"memo": memo}
    except Exception as exc:
        return {"errors": [f"synthesize failed: {exc}"]}


def build_graph():
    """Wire the nodes into a linear StateGraph."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("fetch_market", fetch_market_node)
    graph.add_node("fetch_news", fetch_news_node)
    graph.add_node("synthesize", synthesize_node)

    graph.add_edge(START, "planner")
    # Fan-out: BOTH fetchers branch off the planner and run concurrently.
    graph.add_edge("planner", "fetch_market")
    graph.add_edge("planner", "fetch_news")
    # Fan-in: synthesize waits for BOTH fetchers to finish.
    graph.add_edge("fetch_market", "synthesize")
    graph.add_edge("fetch_news", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
