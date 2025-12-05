# Monad Agent Backend (Skeleton)

This folder contains the initial FastAPI skeleton for the Monad spot trading agent described in `autonomous-monad-agent-prd.md`.

## Features
- FastAPI app with health and agent state endpoints.
- Symphony API client wrappers for supported assets, token prices, and batch swaps.
- Stubbed research client ready for integrating SerpAPI or another search provider.
- SQLAlchemy models representing the minimal database schema outlined in the PRD.

## Getting Started
1. Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Export environment variables for Symphony and OpenAI keys as needed:
   ```bash
   export SYMPHONY_API_KEY=your_key
   export SYMPHONY_SPOT_AGENT_ID=3d8364d0-cfd0-4d16-95c9-1505fa747e10
   ```
3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will expose `/api/health` and `/api/agent/state` with stubbed responses while the agent logic is built out.
