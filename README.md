# FinSight AI

**An autonomous AI research analyst for US equities.**

Give it a stock ticker (e.g., `NVDA`). It reads the latest market data, news, and SEC filings (10-K/10-Q), then delivers a fully cited investment memo. Every claim links back to its evidence. Ask follow-up questions and it answers using only the research it already performed.

**Live demo**: Not soon atleast lol!

**Status**: 🚧 In progress and cooking (June 2026)

## What It Does (v0.1)

1. **Input**: Ticker symbol
2. **Parallel research**: Price/fundamentals snapshot, recent news, latest 10-K/10-Q (Risk Factors + MD&A), local FinBERT sentiment
3. **Evidence layer**: Every fact is stored as a numbered `Evidence` object with source, content, and metadata
4. **Synthesis**: A structured investment memo (thesis, opportunities, risks, snapshot, sentiment) where **every claim cites evidence IDs**
5. **Critic loop**: One bounded revision pass to fix unsupported claims
6. **Q&A**: Retrieval-augmented answers with inline citations over the gathered evidence only
7. **Streaming UX**: Watch the agent work in real time ("Reading 10-K Item 1A…", "Synthesizing memo…")

### Non-Goals (v1)
- No trading signals or price predictions
- Not investment advice (hard-coded disclaimer on every output)
- No portfolio tracking, multi-ticker comparison, or user auth
- US-listed equities only (graceful handling for foreign filers/ETFs/invalid tickers)
- English only

## Architecture

```mermaid
flowchart TD
    U[User: ticker] --> V[validate_input]
    V --> P[planner · nano model]
    P --> F1[fetch_market_data]
    P --> F2[fetch_news]
    P --> F3[fetch_filings · EDGAR]
    P --> F4[sentiment · local FinBERT]
    F1 & F2 & F3 & F4 --> X[extract_insights · nano model, map-reduce]
    X --> S[synthesize_memo · mid-tier model, structured output]
    S --> C{critic: all claims supported?}
    C -- fail, rev < 1 --> S
    C -- pass / max rev --> O[finalize: persist + index evidence]
    O --> Q[Q&A subgraph: retrieve k evidence chunks → cited answer]

┌─────────────┐   SSE stream    ┌──────────────────────────────────────────┐
│  Frontend    │◄──────────────►│  FastAPI                                  │
│  (React/Vite │  POST /memo    │  /memo  /memo/{id}  /qa  /health          │
│   animated)  │  POST /qa      │  rate limiting · request IDs · CORS       │
└─────────────┘                 └───────────────┬──────────────────────────┘
                                                │ invoke (thread_id)
                                ┌───────────────▼──────────────────────────┐
                                │  LangGraph StateGraph (the agent)         │
                                │  validate → plan → ┌ fetch_market ┐       │
                                │                    │ fetch_news    │ fan- │
                                │                    │ fetch_filings │ out  │
                                │                    └ run_finbert  ┘       │
                                │  → extract_insights → synthesize          │
                                │  → critic ──(≤1 revision)──► finalize     │
                                └───┬───────────┬───────────┬───────────────┘
                                    │           │           │
                          ┌─────────▼──┐  ┌─────▼─────┐  ┌──▼─────────────┐
                          │ Tool layer  │  │ LLM layer │  │ Storage         │
                          │ yfinance →  │  │ router:   │  │ SQLite/Postgres │
                          │  Finnhub    │  │ nano-tier │  │ (memos, cache,  │
                          │  fallback   │  │ extract / │  │  checkpoints)   │
                          │ EDGAR       │  │ mid-tier  │  │ Chroma (vectors)│
                          │ (edgartools)│  │ synthesize│  └────────────────┘
                          │ News APIs   │  └───────────┘  ┌────────────────┐
                          │ FinBERT     │                 │ Langfuse traces │
                          │ (local)     │                 │ + cost metrics  │
                          └─────────────┘                 └────────────────┘
Core principles (drawn from Anthropic "Building Effective Agents", 12-Factor Agents, and Hamel Husain's eval methodology):

Workflow backbone with minimal agentic hops (planner + critic only)
LLM emits structured payloads (Pydantic); deterministic code executes
Strong grounding contract + bounded loops + binary faithfulness evals
$0 budget using free tiers only

## Tech Stack
Orchestration: LangGraph 1.x (StateGraph + checkpointer)
API: FastAPI + SSE streaming
Frontend: React (Vite) + Tailwind + Framer Motion
Data: "SQLite (dev) / Postgres, Chroma (vectors)"
Tools: "yfinance + Finnhub fallback, edgartools, local FinBERT"
LLMs: "Gemini 2.5 Flash-Lite (extraction/planning), Gemini 2.5 Flash (synthesis/critic), Groq fallback"
Embeddings: bge-small-en-v1.5 (local)
Observability: Langfuse
Deployment: Docker → Hugging Face Spaces

## Disclaimer 
FinSight AI is an educational demonstration tool.Always do your own research and consult qualified financial professionals. Past performance is not indicative of future results. I am not responsible for your loss. 
