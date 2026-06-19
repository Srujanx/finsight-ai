# """Central LLM Client with retry / backoff.
# All Gemini calls go through here
# retry transient errors (503/429/500) with exponential backoff+ jitter.
# config (model names) lives in one place, swappable.
# """

import os
import random
import time

# from typing import TypeVar
from google import genai
from pydantic import BaseModel

# T = TypeVar("T", bound=BaseModel)

# Transient errors worth retrying - 503 - overloaded , 429 - rate limit , 500 - server
_RETRYABLE = ("503", "429", "500", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
_MAX_ATTEMPTS = 4


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc)
    return any(code in msg for code in _RETRYABLE)


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def generate_structured[T: BaseModel](model: str, prompt: str, schema: type[T]) -> T:
    """One structured-output call, retried on transient errors."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                },
            )
            parsed = response.parsed
            if not isinstance(parsed, schema):
                raise ValueError(f"unparseable response for schema {schema.__name__}")
            return parsed
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == _MAX_ATTEMPTS - 1:
                raise
            sleep_s = (2**attempt) + random.uniform(0, 1)
            print(
                f"  [retry {attempt + 1}/{_MAX_ATTEMPTS - 1}] "
                f"{exc.__class__.__name__}, waiting {sleep_s:.1f}s",
                flush=True,
            )
            time.sleep(sleep_s)
    raise last_exc if last_exc is not None else RuntimeError("unreachable")
