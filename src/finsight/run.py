"""Entry point for graph"""

import sys

from dotenv import load_dotenv

from finsight.graph import build_graph
from finsight.state import new_state


def main() -> None:
    load_dotenv()
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    app = build_graph()

    print(f"-> running graph for {ticker}...", flush=True)
    final_state = app.invoke(new_state(ticker))

    print("\n" + "=" * 70 + "\n")
    print(final_state.get("memo_markdown") or "(no memo produced)")
    print("\n--\nEducational tool. Not investment advice.")

    if final_state.get("errors"):
        print("\n[errors logged during run]")
        for err in final_state["error"]:
            print(f"   - {err}")


if __name__ == "__main__":
    main()
