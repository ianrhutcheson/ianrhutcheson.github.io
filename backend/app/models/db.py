from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AgentConfig(Base):
    __tablename__ = "agent_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_weight: Mapped[float] = mapped_column(Float, default=1.0)
    max_daily_loss: Mapped[float] = mapped_column(Float, default=0.0)
    allowlist: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    blocklist: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    auto_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    run_frequency_seconds: Mapped[int] = mapped_column(Integer, default=900)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32))
    trigger: Mapped[str] = mapped_column(String(32), default="manual")
    summary: Mapped[Optional[str]] = mapped_column(String(512))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    trades: Mapped[list[Trade]] = relationship(back_populates="run")
    snapshots: Mapped[list[PortfolioSnapshot]] = relationship(back_populates="run")
    logs: Mapped[list[AgentLog]] = relationship(back_populates="run")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_runs.id"))
    token_in: Mapped[str] = mapped_column(String(64))
    token_out: Mapped[str] = mapped_column(String(64))
    weight: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    tx_reference: Mapped[Optional[str]] = mapped_column(String(128))
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[AgentRun] = relationship(back_populates="trades")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_runs.id"))
    total_value: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[AgentRun] = relationship(back_populates="snapshots")
    positions: Mapped[list[PositionSnapshot]] = relationship(back_populates="snapshot")


class PositionSnapshot(Base):
    __tablename__ = "positions_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolio_snapshots.id"))
    symbol: Mapped[str] = mapped_column(String(32))
    balance: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    value: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)

    snapshot: Mapped[PortfolioSnapshot] = relationship(back_populates="positions")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agent_runs.id"))
    level: Mapped[str] = mapped_column(String(16), default="info")
    category: Mapped[str] = mapped_column(String(32), default="general")
    message: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[Optional[AgentRun]] = relationship(back_populates="logs")
