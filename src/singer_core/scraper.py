"""采集引擎：基于 Playwright 请求拦截的分页数据采集器。

核心思路：
    不通过 DOM 模拟点击分页，而是利用 Playwright 的 page.route() 拦截
    API 请求，直接修改 POST body 中的分页参数（current / size），
    再从响应中提取 JSON 数据。

    这种方式绕过了所有的 DOM 操作，速度更快且更稳定。

工作流程：
    1. 启动无头浏览器，导航到目标页面
    2. 拦截指定 API 请求，注入认证头和分页参数
    3. 监听 API 响应，解析 JSON 提取记录和总页数
    4. 逐页翻页，每页将解析后的记录追加写入 CSV 并保存进度
    5. 支持从断点页码恢复（通过 ProgressTracker）
"""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
from typing import Any

from playwright.async_api import Page, Response, Route, async_playwright
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from singer_core.auth import generate_auth_headers
from singer_core.browser import create_page, launch_browser
from singer_core.config import AppConfig
from singer_core.exporter import CsvExporter
from singer_core.progress import ProgressTracker


class ScraperEngine:
    """基于 Playwright 请求拦截的采集引擎。

    Args:
        config: 应用配置，包含 URL、认证、输出等全部参数。
        console: 可选的 rich Console 实例，提供后启用进度条美化输出。
    """

    def __init__(
        self,
        config: AppConfig,
        *,
        console: Console | None = None,
    ) -> None:
        self._config = config
        self._console = console
        self._progress = ProgressTracker(config.progress_file)
        self._current_page = 1
        self._response_data: dict[str, Any] | None = None
        self._response_event = asyncio.Event()
        self._total_pages = 0
        self._logger = logging.getLogger(__name__)
        self._page: Page | None = None
        self._captured_auth_key: str | None = None

    # ── 公开入口 ──

    async def run(self) -> dict[str, Any] | None:
        """从断点页开始逐页采集，每页追加写 CSV 并保存进度。

        Returns:
            {"pages_fetched": int, "output_path": str} 或 None。
        """
        start_page = self._progress.load() + 1
        self._log_start(start_page)

        output_path = str(
            Path(self._config.output_dir) / self._config.output_filename
        )
        write_header = not Path(output_path).exists()
        pages_fetched = 0
        total_records = 0

        progress, task = self._create_progress()
        try:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                page = await create_page(browser)
                self._page = page

                await self._setup_page(page)
                self._current_page = start_page
                self._response_event.clear()
                self._response_data = None
                await page.goto(self._config.base_url, wait_until="commit")

                try:
                    result = await self._scrape_loop(
                        start_page=start_page,
                        output_path=output_path,
                        write_header=write_header,
                        progress=progress,
                        task=task,
                    )
                    pages_fetched = result["pages_fetched"]
                    total_records = result["total_records"]
                except KeyboardInterrupt:
                    self._logger.info(
                        "Interrupted, progress saved up to page %d",
                        self._progress.load(),
                    )

                await browser.close()
        finally:
            if progress is not None:
                progress.stop()

        if pages_fetched > 0:
            return {
                "pages_fetched": pages_fetched,
                "total_records": total_records,
                "output_path": output_path,
            }
        return None

    # ── 采集循环 ──

    async def _scrape_loop(
        self,
        start_page: int,
        output_path: str,
        write_header: bool,
        progress: Progress | None,
        task: TaskID | None,
    ) -> dict[str, int]:
        """逐页采集、写 CSV、更新进度条。返回统计信息。"""
        page_num = start_page
        pages_fetched = 0
        total_records = 0
        all_fields: list[str] = []

        while True:
            is_first = page_num == start_page and pages_fetched == 0
            records = (
                await self._await_response(page_num)
                if is_first
                else await self._fetch_page(page_num)
            )

            if self._total_pages == 0:
                self._logger.error("No pagination info received, stopping")
                break

            total_records += len(records)

            if records:
                if not all_fields:
                    all_fields = _collect_fields(records)
                with CsvExporter(
                    output_path,
                    all_fields,
                    self._config.export_headers,
                    write_header=write_header,
                ) as exporter:
                    exporter.write_batch(records)
                write_header = False

            self._progress.save(page_num)
            pages_fetched += 1

            if progress is not None and task is not None:
                if pages_fetched == 1:
                    total_to_fetch = self._total_pages - start_page + 1
                    progress.update(task, total=total_to_fetch)
                progress.update(
                    task,
                    advance=1,
                    description=(
                        f"[cyan]Scraping... "
                        f"{total_records:,} records"
                    ),
                )
            else:
                self._logger.info(
                    "Page %d/%d saved, %d records",
                    page_num,
                    self._total_pages,
                    len(records),
                )

            if page_num >= self._total_pages:
                self._log_done()
                break

            page_num += 1
            await asyncio.sleep(random.uniform(6.0, 8.0))

        return {"pages_fetched": pages_fetched, "total_records": total_records}

    # ── 页面拦截 / 响应 ──

    async def _setup_page(self, page: Page) -> None:
        """注册请求拦截和响应监听，只拦截目标 API 路径。"""
        endpoint = self._endpoint_path()

        async def route_handler(route: Route) -> None:
            if endpoint in route.request.url:
                await self._handle_route(route)
            else:
                await route.continue_()

        await page.route(f"**/{endpoint}**", route_handler)
        page.on("response", lambda resp: asyncio.ensure_future(
            self._handle_response(resp)
        ))

    async def _handle_route(self, route: Route) -> None:
        """拦截回调：首次捕获 Auth Key，注入签名和分页参数。"""
        if self._captured_auth_key is None:
            original_key = route.request.headers.get("x-auth-key", "")
            if original_key:
                self._captured_auth_key = original_key
                self._log_auth_captured()

        auth_key = self._captured_auth_key or self._config.auth_key
        headers = {
            **route.request.headers,
            **generate_auth_headers(auth_key, self._config.auth_secret),
        }
        post_data = f"current={self._current_page}&size={self._config.page_size}"
        await route.continue_(headers=headers, post_data=post_data)

    async def _handle_response(self, response: Response) -> None:
        """响应回调：匹配 API 响应，解析 JSON 并触发事件。"""
        if self._endpoint_path() not in response.url:
            return
        try:
            self._response_data = await response.json()
            self._response_event.set()
        except Exception:
            self._logger.warning("Failed to parse response JSON")

    # ── 页面获取 ──

    async def _await_response(
        self, page_num: int, timeout: float = 60.0
    ) -> list[dict[str, Any]]:
        """等待已触发的响应（不 reload），用于 goto 后消费首次响应。"""
        try:
            await asyncio.wait_for(
                self._response_event.wait(), timeout=timeout
            )
        except TimeoutError:
            self._logger.warning(
                "Page %d timeout waiting for initial response", page_num
            )
            return []
        return self._extract_records()

    async def _fetch_page(
        self, page_num: int, max_retries: int = 3
    ) -> list[dict[str, Any]]:
        """reload 页面并等待响应，超时自动重试（最多 max_retries 次）。"""
        self._current_page = page_num

        for attempt in range(1, max_retries + 1):
            self._response_event.clear()
            self._response_data = None

            if self._page is not None:
                await self._page.reload(wait_until="commit")

            try:
                await asyncio.wait_for(
                    self._response_event.wait(), timeout=60.0
                )
            except TimeoutError:
                if self._should_retry(attempt, max_retries, page_num, "timeout"):
                    await asyncio.sleep(2)
                    continue
                return []

            if self._response_data is None:
                if self._should_retry(attempt, max_retries, page_num, "no data"):
                    await asyncio.sleep(2)
                    continue
                return []

            records = self._extract_records()
            if not records and attempt < max_retries:
                self._logger.warning(
                    "Page %d empty records (attempt %d/%d)",
                    page_num, attempt, max_retries,
                )
                await asyncio.sleep(2)
                continue
            return records

        return []

    # ── 响应解析 ──

    def _extract_records(self) -> list[dict[str, Any]]:
        """从 _response_data 中提取记录列表，同时更新 total_pages。"""
        if self._response_data is None:
            return []
        records, total_pages = _parse_response(self._response_data)
        if self._total_pages == 0 and total_pages > 0:
            self._total_pages = total_pages
        return records

    # ── 辅助方法 ──

    def _endpoint_path(self) -> str:
        """从配置的 request_url 中提取 API 路径片段。"""
        return self._config.request_url.split("//")[-1].split("/", 1)[-1]

    def _should_retry(
        self, attempt: int, max_retries: int, page_num: int, reason: str
    ) -> bool:
        """记录警告并返回是否应重试。"""
        if attempt < max_retries:
            self._logger.warning(
                "Page %d %s (attempt %d/%d)",
                page_num, reason, attempt, max_retries,
            )
            return True
        self._logger.error(
            "Page %d failed after %d retries", page_num, max_retries
        )
        return False

    def _log_start(self, start_page: int) -> None:
        if self._console is not None:
            self._console.print(
                f"🚀 [bold]Starting scrape from page {start_page}[/]"
            )
        else:
            self._logger.info("Starting scrape from page %d", start_page)

    def _log_done(self) -> None:
        if self._console is not None:
            self._console.print("✅ [bold green]All pages fetched[/]")
        else:
            self._logger.info("All pages fetched successfully")

    def _log_auth_captured(self) -> None:
        if self._console is not None:
            self._console.print("🔑 [dim]Auth key captured from frontend[/]")
        else:
            self._logger.info("Auth key captured from frontend request")

    def _create_progress(self) -> tuple[Progress | None, TaskID | None]:
        if self._console is None:
            return None, None
        progress = Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("•", style="dim"),
            TimeElapsedColumn(),
            TextColumn("<", style="dim"),
            TimeRemainingColumn(),
            console=self._console,
        )
        progress.start()
        task = progress.add_task("[cyan]Scraping...", total=None)
        return progress, task


# ── 模块级工具函数 ──


def _collect_fields(records: list[dict[str, Any]]) -> list[str]:
    """从记录列表中按出现顺序收集所有字段名（去重保序）。"""
    seen: set[str] = set()
    fields: list[str] = []
    for rec in records:
        for key in rec:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    return fields


def _parse_response(
    data: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """解析 API 响应 JSON，提取记录列表和总页数。

    兼容两种响应结构：
        - 嵌套型: {"data": {"records": [...], "pages": N}}
        - 扁平型: {"records": [...], "pages": N}
    """
    if "data" in data and isinstance(data["data"], dict):
        inner = data["data"]
        records = inner.get("records", [])
        total_pages = inner.get("pages", 0)
        if isinstance(records, list) and isinstance(total_pages, int):
            return records, total_pages

    records = data.get("records", [])
    total_pages = data.get("pages", 0)
    if isinstance(records, list) and isinstance(total_pages, int):
        return records, total_pages

    return [], 0
