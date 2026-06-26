"""Service layer: run the graph and yield progress events for streaming.

Separates graph execution from the web framework — service.py knows nothing
about HTTP, api.py knows nothing about LangGraph. Clean seam (12-Factor).
"""

from collections.abc import AsyncIterator
from typing import Any

from finsight.cache import get_cached_memo, save_memo
from finsight.graph import build_graph
from finsight.render import memo_to_markdown
from finsight.state import new_state

# Human-readable labels for each node, shown in the UI as it runs.
_NODE_LABELS = {
    "planner": "Planning research…",
    "fetch_market": "Fetching market data…",
    "fetch_news": "Reading recent news…",
    "fetch_filings": "Reading the latest 10-K…",
    "extract_insights": "Extracting filing insights…",
    "synthesize": "Writing the memo…",
    "critic": "Fact-checking claims…",
    "finalize": "Finalizing…",
}


async def run_memo_stream(ticker: str) -> AsyncIterator[dict[str, Any]]:
    """Yield progress events, then a final memo (or error) event.

    Each event is a dict the API serializes to SSE. Event shapes:
      {"type": "progress", "step": "...", "label": "..."}
      {"type": "done", "memo_markdown": "..."}
      {"type": "error", "message": "..."}
    """
    ticker = ticker.upper().strip()

    cached = get_cached_memo(ticker)
    if cached is not None:
        yield {"type": "progress", "step": "cache", "label": "Found a cached memo…"}
        yield {"type": "done", "memo_markdown": memo_to_markdown(cached)}
        return

    app = build_graph()
    final_state: dict[str, Any] = {}

    # stream_mode="updates" yields {node_name: partial_state} after each node.
    async for chunk in app.astream(new_state(ticker), stream_mode="updates"):
        for node_name, node_update in chunk.items():
            label = _NODE_LABELS.get(node_name, f"{node_name}…")
            yield {"type": "progress", "step": node_name, "label": label}
            final_state.update(node_update)

    memo = final_state.get("memo")
    if memo is not None:
        save_memo(memo)
        yield {"type": "done", "memo_markdown": memo_to_markdown(memo)}
    else:
        errors = final_state.get("errors", ["unknown error"])
        yield {"type": "error", "message": "; ".join(errors)}
