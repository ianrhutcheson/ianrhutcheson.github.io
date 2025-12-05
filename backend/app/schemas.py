from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentConfigSchema(BaseModel):
    id: int
    max_weight: float = 1.0
    max_daily_loss: float = 0.0
    allowlist: Optional[list[str]] = Field(default_factory=list)
    blocklist: Optional[list[str]] = Field(default_factory=list)
    auto_trading_enabled: bool = False
    run_frequency_seconds: int = 900
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PositionSnapshotSchema(BaseModel):
    symbol: str
    balance: float
    price: float
    value: float
    weight: float

    class Config:
        orm_mode = True


class PortfolioSnapshotSchema(BaseModel):
    id: int
    run_id: int
    total_value: float
    realized_pnl: float
    unrealized_pnl: float
    created_at: datetime
    positions: List[PositionSnapshotSchema] = []

    class Config:
        orm_mode = True


class TradeSchema(BaseModel):
    id: int
    run_id: int
    token_in: str
    token_out: str
    weight: float
    status: str
    tx_reference: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class AgentRunSchema(BaseModel):
    id: int
    status: str
    trigger: str
    summary: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True


class AgentLogSchema(BaseModel):
    id: int
    run_id: Optional[int]
    level: str
    category: str
    message: str
    created_at: datetime

    class Config:
        orm_mode = True


class AgentStateSchema(BaseModel):
    status: str
    message: str
    agent_id: str
    last_run_id: Optional[int]
    last_run_status: Optional[str]
    config: Optional[AgentConfigSchema]


class RunAgentResponse(BaseModel):
    accepted: bool
    run_id: Optional[int]
    status: str
    summary: str
