"""Notes for me


models.py
evidence_ids: list[str] = Field(min_length=1) — a memo section with zero citations cannot exist as a Python object.
The hallucination guardrail is in the type system
 the prompt merely cooperates.

source_type: SourceType with Literal[...] — the model physically cannot label evidence with a made-up source category;
validation rejects it.

Field(default_factory=dict) instead of = {} — a mutable default like {} would be shared across every instance (the classic Python footgun)
default_factory builds a fresh one each time.
"""
