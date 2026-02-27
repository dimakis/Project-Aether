"""Unit tests for the web_search tool.

Tests HTML parsing helpers and the async search function with mocked httpx.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.tools.web_search import (
    _parse_ddg_html,
    _strip_tags,
    get_web_search_tools,
    web_search,
)

_SAMPLE_HTML = """
<div class="result">
  <a class="result__a" href="https://example.com/1">Example <b>One</b></a>
  <td class="result__snippet">First snippet &amp; description</td>
</div>
<div class="result">
  <a class="result__a" href="https://example.com/2">Example Two</a>
  <td class="result__snippet">Second snippet</td>
</div>
<div class="result">
  <a class="result__a" href="https://example.com/3">Example Three</a>
  <td class="result__snippet">Third snippet</td>
</div>
"""


class TestStripTags:
    """Tests for _strip_tags helper."""

    def test_removes_html_tags(self) -> None:
        assert _strip_tags("<b>bold</b> text") == "bold text"

    def test_unescapes_entities(self) -> None:
        assert _strip_tags("fish &amp; chips") == "fish & chips"

    def test_handles_empty_string(self) -> None:
        assert _strip_tags("") == ""


class TestParseDdgHtml:
    """Tests for _parse_ddg_html helper."""

    def test_extracts_results(self) -> None:
        results = _parse_ddg_html(_SAMPLE_HTML)
        assert len(results) == 3
        assert results[0]["url"] == "https://example.com/1"
        assert results[0]["title"] == "Example One"
        assert "First snippet & description" in results[0]["snippet"]

    def test_respects_max_results(self) -> None:
        results = _parse_ddg_html(_SAMPLE_HTML, max_results=1)
        assert len(results) == 1

    def test_returns_empty_for_no_matches(self) -> None:
        results = _parse_ddg_html("<html><body>No results here</body></html>")
        assert results == []


@pytest.mark.asyncio
class TestWebSearch:
    """Tests for the web_search async tool."""

    async def test_formats_results_correctly(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = _SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.tools.web_search.httpx.AsyncClient", return_value=mock_client):
            result = await web_search.ainvoke({"query": "test query"})

        assert "Search results for: test query" in result
        assert "Example One" in result
        assert "https://example.com/1" in result

    async def test_handles_timeout(self) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.tools.web_search.httpx.AsyncClient", return_value=mock_client):
            result = await web_search.ainvoke({"query": "slow query"})

        assert "timed out" in result.lower()

    async def test_handles_no_results(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body>No results</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.tools.web_search.httpx.AsyncClient", return_value=mock_client):
            result = await web_search.ainvoke({"query": "nothing"})

        assert "No results found" in result


class TestGetWebSearchTools:
    """Tests for get_web_search_tools factory."""

    def test_returns_list_with_web_search(self) -> None:
        tools = get_web_search_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "web_search"
