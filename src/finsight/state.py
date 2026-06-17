"""AgentState: the shared dict the flows through every node of the graph

Earlier, main() passed data between functions by hand. Here every node recieves its state,
reads what it wants , and returns a partial update that LangGraph merges in. This is the
spine of the while agent hangs on.
"""

import operator
from typing import Annotated, TypedDict

from finsight.schemas.models import Evidence


class AgentState(TypedDict):
    """State threaded through the graph. Each node returns a partial dict.

    'total=False' is not set. so think of every key as 'may be present'.

    nodes only return the keys they change.

    """

    ticker: str
    evidence: Annotated[list[Evidence], operator.add]
    memo_markdown: str | None
    errors: Annotated[list[str], operator.add]


def new_state(ticker: str) -> AgentState:
    # Build the initial state for run
    return {
        "ticker": ticker,
        "evidence": [],
        "memo_markdown": None,
        "errors": [],
    }
