from fastapi import FastAPI

from .config import settings
from .clients.symphony import SymphonyClient
from .clients.research import ResearchClient


app = FastAPI(title="Monad Agent Backend", version="0.1.0")


@app.on_event("startup")
async def startup_event() -> None:
    # Pre-warm reusable clients
    app.state.symphony_client = SymphonyClient(
        settings.symphony_api_key, settings.symphony_base_url, settings.symphony_spot_agent_id
    )
    app.state.research_client = ResearchClient(settings.serpapi_api_key)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/agent/state")
async def agent_state() -> dict[str, str]:
    return {
        "status": "idle",
        "message": "Agent skeleton initialized. Configure Symphony and database to proceed.",
        "agent_id": settings.symphony_spot_agent_id,
    }
