# PRD – Autonomous Monad Spot Trading Agent (Symphony-Powered)

## 1. Overview

### 1.1 Product Vision
Build a fully autonomous AI trading agent that:
- Trades spot assets on the Monad chain via Symphony’s Spot/Swap API (`/agent/batch-swap`).
- Allocates trades by weight % of balance (0–100).
- Uses an LLM + internet data (search/news/market info) to discover and evaluate tokens, propose trades, and execute within risk constraints.
- Provides a real-time web UI that shows agent “thoughts,” a live PnL chart, and a rolling trade table.

Custody and execution are handled via Symphony’s agent-based model; the app never directly controls private keys.

## 2. Goals & Non-Goals

### 2.1 Goals
1. **Autonomous trading loop**
   - On an interval, the agent checks portfolio & prices, researches tokens, decides whether to trade, and executes via `/agent/batch-swap` with weight (0–100).
2. **Configurable risk / weights**
   - Per-account settings for max % allocation per asset, max daily loss, trade frequency, and allow/block lists.
3. **Transparent UI**
   - Real-time stream of thoughts, trade blotter with statuses, and PnL graph over time.
4. **Safe execution**
   - Backend enforces hard caps on risk/weight% and auto-pauses on certain error/PNL conditions.

### 2.2 Non-Goals (v1)
- No multi-user SaaS onboarding (single user/admin dashboard).
- No derivatives/perp trading (spot only).
- No backtesting UI (future v2).
- No direct private key handling (everything via Symphony).

## 3. Technical Stack

### 3.1 Backend
- Python + FastAPI (Dockerized on Fly.io).
- Postgres database; APScheduler or Fly cron for jobs.
- OpenAI Chat Completions with tool-calling; model configurable (e.g., gpt-4.1, gpt-5.1).

### 3.2 Frontend
- Next.js or React SPA with Tailwind and charting (Recharts/Chart.js).
- Realtime via WebSockets or SSE from FastAPI backend.

### 3.3 Secrets & Config
- Environment variables: `SYMPHONY_API_KEY`, `SYMPHONY_SPOT_AGENT_ID=3d8364d0-cfd0-4d16-95c9-1505fa747e10`, `OPENAI_API_KEY`, optional `SERPAPI_API_KEY`.
- Never commit secret values; they are supplied via environment.

## 4. External APIs: Canonical Interfaces

### 4.1 Symphony Spot/Swap API
Wrap `/agent/batch-swap`, `/agent/token-price`, `/agent/supported-assets` with typed client methods:
- `list_supported_assets(protocol="spot")`
- `get_token_price(input, chainId=143)`
- `batch_swap(agentId, tokenIn, tokenOut, weight, intentOptions?)`

All calls must send `x-api-key: $SYMPHONY_API_KEY`; default `agentId` is `SYMPHONY_SPOT_AGENT_ID`.

### 4.2 Internet / Web Research
Expose `web_search(query: str, num_results: int = 5) -> list[dict]` returning `{title, url, snippet}` records for LLM consumption.

## 5. System Architecture
- Frontend (Next.js SPA) connects to FastAPI REST endpoints and realtime stream.
- Backend modules: SymphonyClient, ResearchClient, PortfolioService, AgentOrchestrator, Scheduler, Events streamer.
- Postgres stores configuration, trades, PnL snapshots, and logs.

## 6. Core Functional Requirements

### 6.1 Agent Loop (Per Run)
1. Fetch configuration: allowed symbols, max weights, daily loss, run frequency, chainId=143.
2. Discover tradable assets: call `/agent/supported-assets?protocol=spot`, filter to Monad, intersect allow/block lists.
3. Fetch prices & portfolio: call `/agent/token-price` per asset; compute total USD value and weights.
4. Research candidates: run `web_search(f"{symbol} monad token")` for top symbols; provide to LLM.
5. LLM constructs trade plan: target weights per symbol (0–100); backend computes delta weights and swaps.
6. Risk & validation: enforce max weight per asset, sell-side weights ≤ 100 per tokenIn, PnL guardrails; fallback to no-trade if invalid.
7. Execute via Symphony: call `/agent/batch-swap` per swap with optional `intentOptions.desiredProtocol`.
8. Update PnL & logs: recompute snapshot via `/agent/token-price`, persist `portfolio_snapshots`, `agent_logs`, emit events (trade, PnL, log).
9. Finish run: mark `agent_runs` entry with status and summary.

## 7. LLM & Tools Design
- Tools exposed: list_supported_spot_assets, get_token_price, web_search, propose_trade_plan (prompt-based), execute_swap.
- System prompt: risk-aware Monad spot trader using Symphony; respect limits, diversify, avoid red flags, use tools instead of raw HTTP, return concise reasoning.

## 8. Frontend Requirements

### 8.1 Dashboard
- Header with agent status, account, controls (auto-trading toggle, Run Now).
- Agent Thoughts / Log console with filters (All, Trades, Errors, Research).
- PnL panel with line chart (realized/unrealized/total) and summary metrics.
- Trade Blotter: time, Token In→Out, Weight %, estimated amount (if available), Status, Tx reference.
- Portfolio Snapshot: symbol, balance, price, value, weight %.

### 8.2 Settings
- Risk & Allocation: max weight per asset, max daily loss, optional max trade weight.
- Universe: allowlist/blocklist of Monad symbols.
- Scheduling: run frequency, trading hours.
- Logging: verbosity toggle.

## 9. Backend API (for Frontend)
- `GET /api/agent/state` → status, last_run_time, config summary, portfolio snippet.
- `POST /api/agent/run` → trigger async run, return run id & accepted flag.
- `GET /api/agent/trades?limit=100&cursor=` → paginated trades.
- `GET /api/agent/pnl?range=30d` → PnL time series.
- `GET /api/agent/logs?limit=100&cursor=` → paginated logs.
- `GET /api/agent/config` and `POST /api/agent/config` with validation.
- Realtime `GET /api/agent/stream` (WebSocket or SSE) emitting log, trade, and PnL events.

## 10. Data Model (DB Schema – Minimal)
- `agent_config`: risk and scheduling settings, allow/block lists, auto-trading flag.
- `agent_runs`: timestamps, status (success/failure/no_trade), trigger, summary.
- `trades`: per run trades with weights, status, tx reference, raw response.
- `portfolio_snapshots`: timestamped total value, realized/unrealized PnL.
- `positions_snapshot`: per snapshot symbol value and weight.
- `agent_logs`: timestamped logs by level/category with messages.

## 11. Deployment & Ops
- Fly.io deploy: Dockerized FastAPI + Uvicorn, `fly.toml` with port/env, health endpoint; migrations on deploy.
- Database: Fly Postgres or external.
- Frontend: separate deploy (Vercel/Netlify) or served via same Fly app.
- Logging/monitoring: capture Symphony, web search, LLM errors; health endpoint; optional Slack/email alerts for repeated failures or auto-pause triggers.

## 12. Implementation Phases
1. **Phase 1 – Skeleton**: FastAPI health endpoint, Symphony client wrappers, web search stub, DB schema & migrations.
2. **Phase 2 – Agent Orchestrator**: implement `run_agent_once()` using config → assets → prices, integrate OpenAI (decision-only), log to DB.
3. **Phase 3 – Trading**: enable `/agent/batch-swap` (with dev dry-run), risk checks, persist trades & PnL snapshots.
4. **Phase 4 – Frontend**: dashboard + settings, PnL chart + blotter, realtime logs via WebSocket/SSE.
5. **Phase 5 – Scheduling & Hardening**: scheduler for periodic runs, circuit breakers & auto-pause on repeated errors or daily loss breach.
