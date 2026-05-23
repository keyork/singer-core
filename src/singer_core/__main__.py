"""CLI 入口：加载配置 → 启动采集引擎，rich 终端美化输出。"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from singer_core.config import load_config
from singer_core.scraper import ScraperEngine


def _setup_logging() -> Console:
    console = Console(log_path=False)
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=False,
                markup=True,
            )
        ],
    )
    return console


async def main() -> None:
    """异步主函数：初始化日志 → 加载 .env 配置 → 运行采集引擎 → 输出汇总。"""
    console = _setup_logging()
    logger = logging.getLogger(__name__)

    console.rule("[bold blue]🎵 Singer-Core[/]")
    console.print("[dim]Playwright-based data collection engine[/]\n")

    config = load_config()
    engine = ScraperEngine(config, console=console)

    start_time = time.perf_counter()
    try:
        result = await engine.run()
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    elapsed = time.perf_counter() - start_time

    if result is not None:
        table = Table(
            title="✅ Scrape Complete",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_row("📊 Pages Fetched", str(result["pages_fetched"]))
        table.add_row("📄 Output File", result["output_path"])
        table.add_row("⏱️  Time Elapsed", f"{elapsed:.1f}s")
        console.print()
        console.print(Panel(table, expand=False))
    else:
        console.print("[bold red]❌ No data fetched[/]")


if __name__ == "__main__":
    asyncio.run(main())
