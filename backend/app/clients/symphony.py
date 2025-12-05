from __future__ import annotations

from typing import Any, Literal, Optional

import httpx


class SymphonyClient:
    """Async client wrapper for Symphony's spot trading APIs."""

    def __init__(
        self, api_key: str, base_url: str = "https://api.symphony.finance", default_agent_id: Optional[str] = None
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_agent_id = default_agent_id
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=self._headers)

    @property
    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    async def list_supported_assets(self, protocol: Literal["spot", "swap"] = "spot") -> Any:
        response = await self._client.get("/agent/supported-assets", params={"protocol": protocol})
        response.raise_for_status()
        return response.json()

    async def get_token_price(self, token: str, chain_id: int = 143) -> Any:
        response = await self._client.get("/agent/token-price", params={"input": token, "chainId": chain_id})
        response.raise_for_status()
        return response.json()

    async def batch_swap(
        self,
        token_in: str,
        token_out: str,
        weight: float,
        *,
        agent_id: Optional[str] = None,
        desired_protocol: Optional[str] = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "agentId": agent_id or self.default_agent_id,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "weight": weight,
        }
        if desired_protocol:
            payload["intentOptions"] = {"desiredProtocol": desired_protocol}

        response = await self._client.post("/agent/batch-swap", json=payload)
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()
