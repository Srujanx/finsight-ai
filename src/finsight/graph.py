"""The LangGraph StateGraph: planner -> parallel fetchers -> synthesize -> END."""

from datetime import date
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from finsight.filings import fetch_filing_evidence
from finsight.llm import generate_structured
from finsight.planner import make_plan
from finsight.render import memo_to_markdown
from finsight.schemas.models import (
    CriticVerdict,
    Evidence,
    FilingInsights,
    InvestmentMemo,
    Snapshot,
)
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


_EXTRACT_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "extract_insights_v1.md"


def extract_insights_node(state: AgentState) -> dict:
    """Map step: distill filing sections into typed insights (Flash-Lite, cheap)."""
    filing_evidence = [e for e in state["evidence"] if e.source_type == "filing"]
    if not filing_evidence:
        return {}  # no filings to extract from; not an error, just skip

    insights_text_parts = []
    for ev in filing_evidence:
        prompt = _EXTRACT_PROMPT.read_text().format(
            ticker=state["ticker"],
            evidence_id=ev.id,
            section_text=ev.content,
        )
        try:
            insights = generate_structured(
                model="gemini-2.5-flash-lite",
                prompt=prompt,
                schema=FilingInsights,
            )
            for risk in insights.risks:
                insights_text_parts.append(
                    f"RISK [{risk.evidence_id}]: {risk.label} — {risk.summary}"
                )
            for theme in insights.themes:
                insights_text_parts.append(
                    f"THEME [{theme.evidence_id}]: {theme.label} — {theme.summary}"
                )
        except Exception as exc:
            return {"errors": [f"extract_insights failed: {exc}"]}

    if not insights_text_parts:
        return {}

    # Add the distilled insights as a new Evidence item synthesis can cite.
    digest = Evidence(
        id="filing_insights",
        source_type="filing",
        title=f"{state['ticker']} distilled filing insights",
        content="\n".join(insights_text_parts),
        meta={"derived": "extraction"},
    )
    return {"evidence": [digest]}


def synthesize_node(state: AgentState) -> dict:
    """Produce a validated InvestmentMemo. Structured output + grounding contract."""
    evidence = state["evidence"]
    if not evidence:
        return {"errors": ["synthesize: no evidence to work with"]}

    critique = state.get("critique")
    revision_note = ""
    if critique is not None and not critique.overall_pass:
        revision_note = f"\n\nREVISION REQUESTED. Fix these issues:\n{critique.revision_guidance}"

    prompt = (
        _SYNTH_PROMPT.read_text().format(
            ticker=state["ticker"],
            evidence=_format_evidence(evidence),
        )
        + revision_note
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


_CRITIC_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "critic_v1.md"


def critic_node(state: AgentState) -> dict:
    """Evaluator: check every memo claim against its cited evidence (binary)."""
    memo = state["memo"]
    if memo is None:
        return {"errors": ["critic: no memo to check"]}
    prompt = _CRITIC_PROMPT.read_text().format(
        evidence=_format_evidence(state["evidence"]),
        memo=memo_to_markdown(memo),
    )
    try:
        verdict = generate_structured(
            model="gemini-2.5-flash",
            prompt=prompt,
            schema=CriticVerdict,
        )
        return {"critique": verdict}
    except Exception as exc:
        # If the critic itself fails, don't block the memo — log and pass through.
        return {"errors": [f"critic failed(memo kept as in): {exc}"]}


def route_after_critic(state: AgentState) -> str:
    """Decide if to revide once or finsih"""
    critique = state["critique"]
    # Finish if: critic passed, critic errored (no verdict), or we already revised.
    if critique is None or critique.overall_pass or state["revision_count"] >= 1:
        return "finalize"
    return "revise"


def finalize_node(state: AgentState) -> dict:
    """Terminal node. The memo is done; this is where persistence/indexing will go."""
    return {}


def build_graph():
    """Wire the nodes: planner -> 3 parallel fetchers -> extract_insights -> synthesize -> END."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("fetch_market", fetch_market_node)
    graph.add_node("fetch_news", fetch_news_node)
    graph.add_node("fetch_filings", fetch_filings_node)
    graph.add_node("extract_insights", extract_insights_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "planner")

    # Fan-out: three fetchers run concurrently off the planner.
    graph.add_edge("planner", "fetch_market")
    graph.add_edge("planner", "fetch_news")
    graph.add_edge("planner", "fetch_filings")

    # Fan-in: all three rejoin at extract_insights.
    graph.add_edge("fetch_market", "extract_insights")
    graph.add_edge("fetch_news", "extract_insights")
    graph.add_edge("fetch_filings", "extract_insights")

    # Then the linear tail.
    graph.add_edge("extract_insights", "synthesize")
    graph.add_edge("synthesize", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"revise": "synthesize", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)

    return graph.compile()
