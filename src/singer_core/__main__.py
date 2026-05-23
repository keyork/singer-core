"""CLI 入口：加载配置 → 启动采集引擎，rich 终端美化输出。"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from rich.align import Align
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from singer_core.config import AppConfig, load_config
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


def _print_banner(console: Console) -> None:
    banner = Text()
    banner.append("🎵 ", style="bold magenta")
    banner.append("Singer-Core", style="bold blue")
    banner.append(" v0.1.0", style="dim")
    banner.append("\n")
    banner.append("   Playwright-based data collection engine", style="dim italic")
    console.print(Align.center(banner))
    console.print()


def _print_config_table(console: Console, config: AppConfig) -> None:
    table = Table(
        show_header=False,
        border_style="dim blue",
        title="[bold]⚙️  Configuration[/]",
        title_style="bold cyan",
        padding=(0, 2),
    )
    table.add_column("Key", style="bold cyan", width=18)
    table.add_column("Value", style="white")

    c = config
    table.add_row("Output", f"📂 {c.output_dir}/{c.output_filename}")
    table.add_row("Page Size", f"📄 {c.page_size} records/page")
    table.add_row("Progress", f"💾 {c.progress_file}")
    table.add_row("Delay", "⏳ 3.0~4.0s between pages")

    console.print(Panel(table, expand=False, border_style="dim"))
    console.print()


async def main() -> None:
    console = _setup_logging()
    _print_banner(console)

    config = load_config()
    _print_config_table(console, config)

    engine = ScraperEngine(config, console=console)

    start_time = time.perf_counter()
    try:
        result = await engine.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️  Interrupted by user[/]")
        sys.exit(0)
    elapsed = time.perf_counter() - start_time

    console.print()

    if result is not None:
        total_records = result.get("total_records", 0)
        pages = result["pages_fetched"]
        speed = total_records / elapsed if elapsed > 0 else 0

        summary = Table(
            show_header=False,
            border_style="green",
            padding=(0, 2),
        )
        summary.add_column("Icon", width=3)
        summary.add_column("Metric", style="bold", width=20)
        summary.add_column("Value", style="white")

        summary.add_row("📊", "Pages Scraped", f"{pages}")
        summary.add_row("📋", "Total Records", f"{total_records:,}")
        summary.add_row("⏱️ ", "Time Elapsed", f"{elapsed:.1f}s")
        summary.add_row("⚡", "Avg Speed", f"{speed:.1f} records/s")
        summary.add_row("📄", "Output File", result["output_path"])

        panel = Panel(
            summary,
            title="[bold green]✅ Scrape Complete[/]",
            border_style="green",
            expand=False,
        )
        console.print(Align.center(panel))
    else:
        console.print(
            Panel(
                "[bold red]No data fetched.[/]\n"
                "[dim]Check .env configuration and network connectivity.[/]",
                title="[bold red]❌ Failed[/]",
                border_style="red",
                expand=False,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
