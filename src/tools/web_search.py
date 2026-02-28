"""Web search tool for domain agents.

Feature 30: Dynamic agent composition -- provides web search capability
for Research, Food, and other domain agents that need external data.

Uses DuckDuckGo's HTML search (no API key required).  Can be upgraded
to Tavily or SerpAPI by setting ``WEB_SEARCH_PROVIDER`` in env.

Constitution Principle VI (Security): input is validated via Pydantic
(LangChain tool schema), results are truncated to prevent prompt
injection from large pages.
"""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any

import httpx
from langchain_core.tools import tool

from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_MAX_RESULTS = 5
_MAX_SNIPPET_CHARS = 300
_REQUEST_TIMEOUT = 15.0

_TAG_RE = re.compile(r"<[^>]+>")
_RESULT_RE = re.compile(
    r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    r".*?"
    r'class="result__snippet"[^>]*>(.*?)</(?:td|div)',
    re.DOTALL,
)


def _strip_tags(html: str) -> str:
    """Remove HTML tags and unescape entities."""
    return unescape(_TAG_RE.sub("", html)).strip()


def _parse_ddg_html(html: str, max_results: int = _MAX_RESULTS) -> list[dict[str, str]]:
    """Extract search results from DuckDuckGo HTML response."""
    results: list[dict[str, str]] = []
    for match in _RESULT_RE.finditer(html):
        if len(results) >= max_results:
            break
        url = match.group(1)
        title = _strip_tags(match.group(2))
        snippet = _strip_tags(match.group(3))[:_MAX_SNIPPET_CHARS]
        if url and title:
            results.append({"url": url, "title": title, "snippet": snippet})
    return results


@tool("web_search")
@trace_with_uri(name="tools.web_search", span_type="TOOL")
async def web_search(
    query: str,
    max_results: int = _MAX_RESULTS,
) -> str:
    """Search the web using DuckDuckGo.

    Returns a formatted list of search results with titles, URLs,
    and snippets.  Useful for finding recipes, prices, news,
    documentation, or any publicly available information.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (1-10, default 5).

    Returns:
        Formatted search results or an error message.
    """
    max_results = min(max(1, max_results), 10)

    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        ) as client:
            response = await client.post(
                _SEARCH_URL,
                data={"q": query},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; Aether/1.0; +https://github.com/aether-home)"
                    ),
                },
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        return f"Web search timed out for query: {query}"
    except httpx.HTTPStatusError as exc:
        return f"Web search failed (HTTP {exc.response.status_code}): {query}"
    except httpx.HTTPError as exc:
        return f"Web search connection error: {exc}"

    results = _parse_ddg_html(response.text, max_results)

    if not results:
        return f"No results found for: {query}"

    lines: list[str] = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   {r['url']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet']}")
        lines.append("")

    return "\n".join(lines)


def get_web_search_tools() -> list[Any]:
    return [web_search]
