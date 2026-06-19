"""Entry point for the FinSight graph.

Run with:  uv run python -m finsight.run NVDA
"""

import sys

from dotenv import load_dotenv

from finsight.cache import get_cached_memo, save_memo
from finsight.graph import build_graph
from finsight.render import memo_to_markdown
from finsight.state import new_state


def main() -> None:
    load_dotenv()
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"

    cached = get_cached_memo(ticker)
    if cached is not None:
        print(f"-> cache HIT for {ticker} (zero quota spent)", flush=True)
        memo = cached
    else:
        print(f"-> cache MISS — running graph for {ticker}...", flush=True)
        app = build_graph()
        final_state = app.invoke(new_state(ticker))
        memo = final_state.get("memo")
        if memo is not None:
            save_memo(memo)
        if final_state.get("errors"):
            print("\n[errors logged during run]")
            for err in final_state["errors"]:
                print(f"  - {err}")

    print("\n" + "=" * 70 + "\n")
    print(memo_to_markdown(memo) if memo is not None else "(no memo produced)")


if __name__ == "__main__":
    main()
