from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from .clients.research import ResearchClient
from .clients.symphony import SymphonyClient
from .config import settings
from .database import get_db
from .models.db import AgentConfig, AgentLog, AgentRun, PortfolioSnapshot, Trade
from .schemas import (
    AgentConfigSchema,
    AgentLogSchema,
    AgentRunSchema,
    AgentStateSchema,
    PortfolioSnapshotSchema,
    RunAgentResponse,
    TradeSchema,
)
from .services.orchestrator import AgentOrchestrator


app = FastAPI(title="Monad Agent Backend", version="0.2.0")


@app.on_event("startup")
async def startup_event() -> None:
    app.state.symphony_client = SymphonyClient(
        settings.symphony_api_key, settings.symphony_base_url, settings.symphony_spot_agent_id
    )
    app.state.research_client = ResearchClient(settings.serpapi_api_key)
    app.state.orchestrator = AgentOrchestrator(app.state.symphony_client, app.state.research_client)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await app.state.symphony_client.aclose()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/agent/state", response_model=AgentStateSchema)
async def agent_state(db: Session = Depends(get_db)) -> AgentStateSchema:
    config = db.query(AgentConfig).order_by(AgentConfig.id.desc()).first()
    last_run = db.query(AgentRun).order_by(AgentRun.started_at.desc()).first()
    status = last_run.status if last_run else "idle"
    message = last_run.summary if last_run else "Agent skeleton initialized. Configure Symphony and database to proceed."
    return AgentStateSchema(
        status=status,
        message=message,
        agent_id=settings.symphony_spot_agent_id,
        last_run_id=last_run.id if last_run else None,
        last_run_status=last_run.status if last_run else None,
        config=config,
    )


@app.post("/api/agent/run", response_model=RunAgentResponse)
async def run_agent(trigger: str = "manual", db: Session = Depends(get_db)) -> RunAgentResponse:
    orchestrator: AgentOrchestrator = app.state.orchestrator
    run = await orchestrator.run_once(db, trigger=trigger)
    accepted = run.status in {"running", "success", "pending", "submitted"}
    summary = run.summary or "Run created"
    return RunAgentResponse(accepted=accepted, run_id=run.id, status=run.status, summary=summary)


@app.get("/api/agent/config", response_model=AgentConfigSchema)
async def get_config(db: Session = Depends(get_db)) -> AgentConfigSchema:
    config = db.query(AgentConfig).order_by(AgentConfig.id.desc()).first()
    if not config:
        config = AgentConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@app.post("/api/agent/config", response_model=AgentConfigSchema)
async def update_config(payload: AgentConfigSchema, db: Session = Depends(get_db)) -> AgentConfigSchema:
    config = db.get(AgentConfig, payload.id)
    if not config:
        config = AgentConfig()
        db.add(config)

    config.max_weight = payload.max_weight
    config.max_daily_loss = payload.max_daily_loss
    config.allowlist = payload.allowlist
    config.blocklist = payload.blocklist
    config.auto_trading_enabled = payload.auto_trading_enabled
    config.run_frequency_seconds = payload.run_frequency_seconds
    db.commit()
    db.refresh(config)
    return config


@app.get("/api/agent/runs", response_model=list[AgentRunSchema])
async def list_runs(limit: int = 20, db: Session = Depends(get_db)) -> list[AgentRun]:
    return db.query(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit).all()


@app.get("/api/agent/trades", response_model=list[TradeSchema])
async def list_trades(limit: int = 50, db: Session = Depends(get_db)) -> list[Trade]:
    return db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()


@app.get("/api/agent/logs", response_model=list[AgentLogSchema])
async def list_logs(limit: int = 100, db: Session = Depends(get_db)) -> list[AgentLog]:
    return db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(limit).all()


@app.get("/api/agent/pnl", response_model=list[PortfolioSnapshotSchema])
async def list_pnl(limit: int = 50, db: Session = Depends(get_db)) -> list[PortfolioSnapshot]:
    return db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc()).limit(limit).all()
