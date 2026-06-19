from typing import Any

import pytest
from pydantic import ValidationError

from finsight.schemas.models import Evidence, InvestmentMemo, MemoSection, Snapshot


def make_evidence(**overrides: Any) -> Evidence:
    base: dict[str, Any] = {
        "id": "news_01",
        "source_type": "news",
        "title": "NVDA ships new chips",
        "url": "https://example.com/article",
        "content": "NVIDIA announced a new accelerator today.",
    }

    base.update(overrides)
    return Evidence(**base)


def test_valid_evidence_builds():
    ev = make_evidence()
    assert ev.id == "news_01"
    assert ev.meta == {}


def test_evidence_rejects_unknown_source_type():
    with pytest.raises(ValidationError):
        make_evidence(source_type="rumor")


def test_memo_section_allows_empty_evidence_at_schema_level():
    # Schema is shape-only for Gemini free-tier compatibility;
    # the grounding contract is enforced in synthesize_node, not here.
    section = MemoSection(heading="Risks", body_md="Something.", evidence_ids=[])
    assert section.evidence_ids == []


def test_memo_section_with_evidence_passes():
    section = MemoSection(heading="Risks", body_md="Something risks", evidence_ids=["news_01"])
    assert section.evidence_ids == ["news_01"]


def test_full_memo_build():
    thesis = MemoSection(heading="Thesis", body_md="Solid.", evidence_ids=["px_snapshot"])
    memo = InvestmentMemo(
        ticker="NVDA",
        company="NVIDIA Corperation",
        as_of="2026-06-13",
        snapshot=Snapshot(price="123.45"),
        thesis=thesis,
        disclaimer="Educational tool. Not Investment Advice.",
    )

    assert memo.risks == []
