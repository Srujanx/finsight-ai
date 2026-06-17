"""The LangGraph StateGraph: linear pipeline, same output

fetch_market -> fetch_news -> sythesize -> END
"""

from datetime import UTC, datetime

from langgraph.graph import END, START, StateGraph

from finsight.schemas.models import Evidence
from finsight.state import AgentState
from finsight.tracer import build_prompt, generate_memo, get_headlines, get_snapshot


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


def synthesize_node(state: AgentState) -> dict:
    # Reads evidence back out of state

    # Reconstructing the snapchat dict and headline list from evidence
    snapshot: dict = {}
    headlines: list[dict] = []
    for ev in state["evidence"]:
        if ev.source_type == "market":
            snapshot = ev.meta
        elif ev.source_type == "news":
            headlines.append({"headline": ev.title, "source": ev.meta.get("source", "")})

    prompt = build_prompt(snapshot, headlines)
    memo = generate_memo(prompt)
    stamped = f"{memo}\n\n_Generated {datetime.now(UTC).isoformat()}_"
    return {"memo_markdown": stamped}


def build_graph():
    """Wire the nodes into a linear StateGraph."""
    graph = StateGraph(AgentState)
    graph.add_node("fetch_market", fetch_market_node)
    graph.add_node("fetch_news", fetch_news_node)
    graph.add_node("synthesize", synthesize_node)

    graph.add_edge(START, "fetch_market")
    graph.add_edge("fetch_market", "fetch_news")
    graph.add_edge("fetch_news", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
