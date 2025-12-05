from __future__ import annotations

from typing import Any, Iterable


class ResearchClient:
    """Stubbed research client for token discovery and news search."""

    def __init__(self, serpapi_api_key: str) -> None:
        self.serpapi_api_key = serpapi_api_key

    async def web_search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        """Return placeholder search results until an external search API is wired up."""
        return [
            {
                "title": f"{query} result {i+1}",
                "url": "https://example.com",
                "snippet": "Stubbed search result — connect to SerpAPI or another provider.",
            }
            for i in range(num_results)
        ]

    @staticmethod
    def summarize_links(links: Iterable[dict[str, Any]]) -> list[str]:
        return [f"{item.get('title')}: {item.get('url')}" for item in links]
