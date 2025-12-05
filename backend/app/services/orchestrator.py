from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from ..clients.research import ResearchClient
from ..clients.symphony import SymphonyClient
from ..config import settings
from ..models.db import (
    AgentConfig,
    AgentLog,
    AgentRun,
    PortfolioSnapshot,
    PositionSnapshot,
    Trade,
)


class AgentOrchestrator:
    """Minimal agent runner that ties together Symphony, research, and persistence."""

    def __init__(
        self,
        symphony_client: SymphonyClient,
        research_client: ResearchClient,
    ) -> None:
        self.symphony_client = symphony_client
        self.research_client = research_client

    async def run_once(self, db: Session, *, trigger: str = "manual") -> AgentRun:
        run = AgentRun(status="running", trigger=trigger, started_at=datetime.utcnow())
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            config = self._get_or_create_config(db)
            self._log(db, f"Starting agent run (simulate_only={settings.simulate_only})", run)

            assets = await self._discover_assets()
            filtered_assets = self._apply_universe_filters(assets, config.allowlist or [], config.blocklist or [])
            if not filtered_assets:
                raise RuntimeError("No assets available after allow/block filters")

            priced_assets = await self._get_prices(filtered_assets)
            trade_plan = self._propose_simple_plan(priced_assets, max_weight=config.max_weight)

            trades = await self._execute_trades(db, run, trade_plan, simulate=settings.simulate_only)
            snapshot = await self._record_snapshot(db, run, priced_assets)

            run.status = "success"
            run.summary = f"Executed {len(trades)} trades; portfolio value=${snapshot.total_value:,.2f}"
            run.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(run)
            self._log(db, run.summary, run, category="summary")
        except Exception as exc:  # noqa: BLE001 - top level guard for agent loop
            db.rollback()
            run.status = "failed"
            run.summary = str(exc)
            run.completed_at = datetime.utcnow()
            db.add(run)
            db.commit()
            self._log(db, f"Run failed: {exc}", run, level="error", category="error")
        return run

    def _get_or_create_config(self, db: Session) -> AgentConfig:
        config = db.query(AgentConfig).order_by(AgentConfig.id.desc()).first()
        if not config:
            config = AgentConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    async def _discover_assets(self) -> list[dict[str, Any]]:
        try:
            response = await self.symphony_client.list_supported_assets("spot")
            return response.get("tokens", []) if isinstance(response, dict) else response
        except Exception:
            # Fall back to static Monad spot tokens to allow dev/testing
            return [
                {"symbol": "USDC", "chainId": settings.default_chain_id},
                {"symbol": "MON", "chainId": settings.default_chain_id},
                {"symbol": "ETH", "chainId": settings.default_chain_id},
            ]

    @staticmethod
    def _apply_universe_filters(assets: Iterable[dict[str, Any]], allow: list[str], block: list[str]) -> list[dict[str, Any]]:
        formatted_allow = {item.upper() for item in allow} if allow else None
        block_set = {item.upper() for item in block}

        filtered = []
        for asset in assets:
            symbol = str(asset.get("symbol", "")).upper()
            if formatted_allow and symbol not in formatted_allow:
                continue
            if symbol in block_set:
                continue
            if int(asset.get("chainId", settings.default_chain_id)) != settings.default_chain_id:
                continue
            filtered.append(asset)
        return filtered

    async def _get_prices(self, assets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        priced = []
        for asset in assets:
            symbol = asset.get("symbol")
            price = 1.0
            try:
                result = await self.symphony_client.get_token_price(symbol, chain_id=settings.default_chain_id)
                if isinstance(result, dict):
                    price = float(result.get("price", price))
            except Exception:
                # keep fallback price
                price = price
            priced.append({"symbol": symbol, "price": price, "weight": 0.0, "balance": 1.0})
        return priced

    def _propose_simple_plan(self, priced_assets: list[dict[str, Any]], max_weight: float) -> list[dict[str, Any]]:
        trades = []
        if len(priced_assets) < 2:
            return trades
        target_weight = min(max_weight, 0.25)
        token_in = priced_assets[0]["symbol"]
        for asset in priced_assets[1:3]:
            trades.append({
                "token_in": token_in,
                "token_out": asset["symbol"],
                "weight": target_weight,
            })
        return trades

    async def _execute_trades(
        self,
        db: Session,
        run: AgentRun,
        trade_plan: list[dict[str, Any]],
        *,
        simulate: bool = False,
    ) -> list[Trade]:
        executed: list[Trade] = []
        for plan in trade_plan:
            status = "simulated" if simulate or not settings.symphony_api_key else "pending"
            tx_ref: Optional[str] = None
            raw_response: Optional[dict[str, Any]] = None

            if not simulate and settings.symphony_api_key:
                try:
                    resp = await self.symphony_client.batch_swap(
                        plan["token_in"], plan["token_out"], plan["weight"], agent_id=settings.symphony_spot_agent_id
                    )
                    raw_response = resp if isinstance(resp, dict) else None
                    tx_ref = raw_response.get("txHash") if isinstance(raw_response, dict) else None
                    status = "submitted"
                except Exception as exc:
                    status = "error"
                    self._log(db, f"Trade failed: {exc}", run, level="error", category="trade")

            trade = Trade(
                run_id=run.id,
                token_in=plan["token_in"],
                token_out=plan["token_out"],
                weight=plan["weight"],
                status=status,
                tx_reference=tx_ref,
                raw_response=raw_response,
                created_at=datetime.utcnow(),
            )
            db.add(trade)
            executed.append(trade)
        db.commit()
        for trade in executed:
            db.refresh(trade)
        return executed

    async def _record_snapshot(self, db: Session, run: AgentRun, priced_assets: list[dict[str, Any]]) -> PortfolioSnapshot:
        total_value = sum(asset["price"] * asset.get("balance", 1.0) for asset in priced_assets)
        snapshot = PortfolioSnapshot(
            run_id=run.id,
            total_value=total_value,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            created_at=datetime.utcnow(),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        positions = []
        for asset in priced_assets:
            positions.append(
                PositionSnapshot(
                    snapshot_id=snapshot.id,
                    symbol=asset["symbol"],
                    balance=asset.get("balance", 1.0),
                    price=asset.get("price", 0.0),
                    value=asset.get("price", 0.0) * asset.get("balance", 1.0),
                    weight=asset.get("weight", 0.0),
                )
            )
        db.add_all(positions)
        db.commit()
        return snapshot

    def _log(
        self,
        db: Session,
        message: str,
        run: Optional[AgentRun] = None,
        *,
        level: str = "info",
        category: str = "general",
    ) -> None:
        log = AgentLog(
            run_id=run.id if run else None,
            level=level,
            category=category,
            message=message,
            created_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
