# Render a structured InvestMentMemo as markdown for terminal/display
from finsight.schemas.models import InvestmentMemo, MemoSection


def _section_md(section: MemoSection) -> str:
    cities = " ".join(f"[{eid}]" for eid in section.evidence_ids)
    return f"#### {section.heading} {cities}\n\n{section.body_md}\n"


def memo_to_markdown(memo: InvestmentMemo) -> str:
    parts = [f"# {memo.company} ({memo.ticker})", f"_As of {memo.as_of}_\n"]
    snap = memo.snapshot
    parts.append(
        f"**Snapshot:** price {snap.price}, mkt cap {snap.market_cap}, "
        f"P/E {snap.pe_ratio}, 52w {snap.fifty_two_week_low}–{snap.fifty_two_week_high}\n"
    )
    parts.append(_section_md(memo.thesis))
    if memo.opportunities:
        parts.append("##Opportunities\n")
        parts.extend(_section_md(s) for s in memo.opportunities)
    if memo.risks:
        parts.append("##Risks\n")
        parts.extend(_section_md(s) for s in memo.risks)
    if memo.open_questions:
        parts.append("## Open Questions\n")
        parts.extend(f" - {q}" for q in memo.open_questions)
    parts.append(f"\n --- \n_{memo.disclaimer}_")
    return "\n".join(parts)
