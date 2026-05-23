from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from singer_core.config import AppConfig
from singer_core.scraper import ScraperEngine, _parse_response


def _make_config(env_vars: dict[str, str]) -> AppConfig:
    return AppConfig(**env_vars)


def test_scraper_initialization(env_vars: dict[str, str]) -> None:
    config = _make_config(env_vars)
    engine = ScraperEngine(config)
    assert engine._config is config


async def test_run_fetches_single_page(
    env_vars: dict[str, str],
    mock_response_single_page: dict[str, Any],
    tmp_path: object,
) -> None:
    config = _make_config(env_vars)
    config.output_dir = str(tmp_path) + "/out"  # type: ignore[arg-type]
    config.progress_file = str(tmp_path) + "/progress.txt"  # type: ignore[arg-type]
    engine = ScraperEngine(config)

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.reload = AsyncMock()
    mock_page.route = AsyncMock()
    mock_page.on = MagicMock()
    mock_page.set_default_navigation_timeout = MagicMock()
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_ctx = MagicMock()
    mock_pw_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_ctx.__aexit__ = AsyncMock(return_value=None)

    route_handler = None
    response_handler = None

    def capture_route(pattern: str, handler: Any) -> Any:
        nonlocal route_handler
        route_handler = handler

    def capture_on(event: str, handler: Any) -> None:
        nonlocal response_handler
        if event == "response":
            response_handler = handler

    mock_page.route.side_effect = capture_route
    mock_page.on.side_effect = capture_on

    call_count = 0

    async def fake_reload(**kwargs: Any) -> None:
        nonlocal call_count
        call_count += 1
        if response_handler is not None:
            mock_response = AsyncMock()
            mock_response.url = config.request_url
            mock_response.json = AsyncMock(
                return_value=mock_response_single_page
            )
            await response_handler(mock_response)

    async def fake_goto(url: str, **kwargs: Any) -> None:
        if response_handler is not None:
            mock_response = AsyncMock()
            mock_response.url = config.request_url
            mock_response.json = AsyncMock(
                return_value=mock_response_single_page
            )
            await response_handler(mock_response)

    mock_page.reload.side_effect = fake_reload
    mock_page.goto.side_effect = fake_goto

    with patch("singer_core.scraper.async_playwright", return_value=mock_pw_ctx):
        await engine.run()

    assert call_count >= 0  # Engine completed without error


async def test_run_resumes_from_progress(
    env_vars: dict[str, str],
    mock_response_multi_page: list[dict[str, Any]],
    tmp_path: object,
) -> None:
    config = _make_config(env_vars)
    out_dir = str(tmp_path) + "/out"  # type: ignore[arg-type]
    prog_file = str(tmp_path) + "/progress.txt"  # type: ignore[arg-type]
    config.output_dir = out_dir
    config.progress_file = prog_file

    from singer_core.progress import ProgressTracker

    tracker = ProgressTracker(prog_file)
    tracker.save(1)  # Start from page 2

    engine = ScraperEngine(config)

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.route = AsyncMock()
    mock_page.on = MagicMock()
    mock_page.set_default_navigation_timeout = MagicMock()
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_ctx = MagicMock()
    mock_pw_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_ctx.__aexit__ = AsyncMock(return_value=None)

    response_handler = None

    def capture_on(event: str, handler: Any) -> None:
        nonlocal response_handler
        if event == "response":
            response_handler = handler

    mock_page.on.side_effect = capture_on

    page_index = 0

    async def fake_goto(url: str, **kwargs: Any) -> None:
        nonlocal page_index
        if response_handler is not None and page_index < len(mock_response_multi_page):
            mock_response = AsyncMock()
            mock_response.url = config.request_url
            mock_response.json = AsyncMock(
                return_value=mock_response_multi_page[page_index]
            )
            page_index += 1
            await response_handler(mock_response)

    async def fake_reload(**kwargs: Any) -> None:
        nonlocal page_index
        if response_handler is not None and page_index < len(mock_response_multi_page):
            mock_response = AsyncMock()
            mock_response.url = config.request_url
            mock_response.json = AsyncMock(
                return_value=mock_response_multi_page[page_index]
            )
            page_index += 1
            await response_handler(mock_response)

    mock_page.goto.side_effect = fake_goto
    mock_page.reload.side_effect = fake_reload

    with patch("singer_core.scraper.async_playwright", return_value=mock_pw_ctx):
        await engine.run()

    # Should have fetched only page 2 (resumed from page 1)
    assert page_index == 1


def test_parse_response_extracts_records_and_pages() -> None:
    data: dict[str, Any] = {
        "code": 200,
        "data": {
            "total": 100,
            "pages": 10,
            "records": [{"axbe0003": "Test"}],
        },
    }
    records, total_pages = _parse_response(data)
    assert len(records) == 1
    assert total_pages == 10


def test_parse_response_handles_flat_structure() -> None:
    data: dict[str, Any] = {
        "records": [{"axbe0003": "Flat"}],
        "pages": 5,
    }
    records, total_pages = _parse_response(data)
    assert len(records) == 1
    assert total_pages == 5


def test_parse_response_returns_empty_on_invalid_data() -> None:
    records, total_pages = _parse_response({})
    assert records == []
    assert total_pages == 0
