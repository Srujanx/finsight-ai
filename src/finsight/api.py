"""FastAPI app: HTTP + SSE wrapper around the service layer.

Knows nothing about LangGraph — just turns service events into SSE.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from finsight.service import run_memo_stream

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="FinSight AI")

# CORS: allow the frontend (same origin in prod, localhost in dev) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your domain after deploy if you like
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/memo/{ticker}")
@limiter.limit("10/hour")  # public-demo abuse guard (bible §7.7)
async def memo(request: Request, ticker: str):
    """Stream a memo for a ticker as Server-Sent Events."""

    async def event_generator():
        import json

        async for event in run_memo_stream(ticker):
            if await request.is_disconnected():
                break
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())
