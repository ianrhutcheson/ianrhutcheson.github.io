# Monad Agent Backend

Production-ready FastAPI backend for the Monad spot trading agent described in `autonomous-monad-agent-prd.md`. It exposes REST endpoints for health, configuration, logs, trades, and an on-demand agent loop. A Dockerfile and `fly.toml` are provided for Fly.io deployment.

## Features
- FastAPI service with `/api/health`, `/api/agent/state`, `/api/agent/run`, `/api/agent/config`, `/api/agent/trades`, `/api/agent/logs`, and `/api/agent/pnl`.
- Symphony client wrappers for supported assets, token prices, and batch swaps (supports simulation mode without API keys).
- Lightweight research client and minimal orchestrator that discovers assets, proposes a simple trade plan, executes simulated or live swaps, and records portfolio/log entries.
- SQLAlchemy models and automatic table creation for configuration, runs, trades, PnL snapshots, and logs.
- Dockerfile and Fly.io config for deployment on port 8080.

## Getting Started Locally
1. Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Export environment variables (simulation is enabled by default so keys are optional):
   ```bash
   export SYMPHONY_API_KEY=your_key              # optional when SIMULATE_ONLY=true
   export SYMPHONY_SPOT_AGENT_ID=3d8364d0-cfd0-4d16-95c9-1505fa747e10
   export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/monad_agent
   export SIMULATE_ONLY=true
   ```
3. Run the development server:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

## Running the Agent Loop
Trigger an agent run and view state:
```bash
curl -X POST http://localhost:8080/api/agent/run
curl http://localhost:8080/api/agent/state
```

## Deploying to Fly.io
1. Authenticate with Fly and create (or reuse) an app matching the name in `fly.toml`:
   ```bash
   fly auth login
   fly apps create monad-agent-backend
   ```
2. Set required secrets (replace values as needed):
   ```bash
   fly secrets set SYMPHONY_API_KEY=... SYMPHONY_SPOT_AGENT_ID=3d8364d0-cfd0-4d16-95c9-1505fa747e10
   fly secrets set DATABASE_URL=postgresql+psycopg://<user>:<pass>@<host>:5432/monad_agent
   fly secrets set SIMULATE_ONLY=false
   ```
3. Deploy from the `backend` directory:
   ```bash
   fly deploy
   ```

The app listens on port 8080 and exposes health and agent endpoints ready for integration with a frontend or monitoring tools.
