"""The LangGraph StateGraph: planner -> parallel fetchers -> synthesize -> END."""

from datetime import date
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from finsight.filings import fetch_filing_evidence
from finsight.llm import generate_structured
from finsight.planner import make_plan
from finsight.schemas.models import Evidence, InvestmentMemo, Snapshot
from finsight.state import AgentState
from finsight.tracer import get_headlines, get_snapshot

_SYNTH_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "synthesize_memo_v1.md"


def planner_node(state: AgentState) -> dict:
    """First agentic decision point: decide what matters for this company."""
    try:
        plan = make_plan(state["ticker"])
        return {"plan": plan}
    except Exception as exc:
        return {"errors": [f"planner failed: {exc}"]}


def fetch_market_node(state: AgentState) -> dict:
    """Wrap get_snapshot. Returns Evidence to be appended."""
    ticker = state["ticker"]
    try:
        snap = get_snapshot(ticker)
        ev = Evidence(
            id="px_snapshot",
            source_type="market",
            title=f"{snap.get('name', ticker)} market snapshot",
            content=str(snap),
            meta={k: str(v) for k, v in snap.items()},
        )
        return {"evidence": [ev]}
    except Exception as exc:
        return {"errors": [f"fetch_market failed: {exc}"]}


def fetch_news_node(state: AgentState) -> dict:
    """Wrap get_headlines. One Evidence per headline."""
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


def fetch_filings_node(state: AgentState) -> dict:
    """Wrap EDGAR filing fetcher. Empty evidence if no 10-K (graceful)"""
    try:
        evidence = fetch_filing_evidence(state["ticker"])
        if not evidence:
            return {"errors": [f"no 10-K parsed for {state['ticker']}"]}
        return {"evidence": evidence}
    except Exception as exc:
        return {"errors": [f"fetch_filings failed: {exc}"]}


def _format_evidence(evidence: list[Evidence]) -> str:
    """Render evidence as a labeled block the model can cite by id."""
    lines = []
    for ev in evidence:
        lines.append(f"[{ev.id}] ({ev.source_type}) {ev.title}\n{ev.content}\n")
    return "\n".join(lines)


def synthesize_node(state: AgentState) -> dict:
    """Produce a validated InvestmentMemo. Structured output + grounding contract."""
    evidence = state["evidence"]
    if not evidence:
        return {"errors": ["synthesize: no evidence to work with"]}

    prompt = _SYNTH_PROMPT.read_text().format(
        ticker=state["ticker"],
        evidence=_format_evidence(evidence),
    )

    try:
        memo = generate_structured(
            model="gemini-2.5-flash",
            prompt=prompt,
            schema=InvestmentMemo,
        )
        memo.ticker = state["ticker"]
        memo.as_of = date.today().isoformat()
        snap_ev = next((e for e in evidence if e.source_type == "market"), None)
        if snap_ev is not None:
            m = snap_ev.meta
            memo.snapshot = Snapshot(
                price=m.get("price", ""),
                market_cap=m.get("market_cap", ""),
                pe_ratio=m.get("trailing_pe", ""),
                fifty_two_week_high=m.get("fifty_two_week_high", ""),
                fifty_two_week_low=m.get("fifty_two_week_low", ""),
                sector=m.get("sector", ""),
            )
        all_sections = [memo.thesis, *memo.opportunities, *memo.risks]
        ungrounded = [s.heading for s in all_sections if not s.evidence_ids]
        if ungrounded:
            return {"errors": [f"grounding violated — uncited sections: {ungrounded}"]}
        return {"memo": memo}
    except Exception as exc:
        return {"errors": [f"synthesize failed: {exc}"]}


def build_graph():
    """Wire the nodes: planner -> parallel fetchers -> synthesize -> END."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("fetch_market", fetch_market_node)
    graph.add_node("fetch_filings", fetch_filings_node)
    graph.add_node("fetch_news", fetch_news_node)
    graph.add_node("synthesize", synthesize_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "fetch_market")
    graph.add_edge("planner", "fetch_news")
    graph.add_edge("fetch_market", "synthesize")
    graph.add_edge("fetch_news", "synthesize")
    graph.add_edge("planner", "fetch_filings")
    graph.add_edge("fetch_filings", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
