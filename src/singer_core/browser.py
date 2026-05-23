"""浏览器管理：启动、页面配置、反检测。

负责 Playwright 浏览器的生命周期管理，包括：
    - 无头 Chromium 启动（含反自动化检测参数）
    - 自定义 User-Agent 的浏览器上下文
    - 页面创建与超时配置
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser, Page, Playwright

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_NAVIGATION_TIMEOUT = 90_000


async def launch_browser(p: Playwright) -> Browser:
    """启动无头 Chromium，注入反自动化检测参数。"""
    return await p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )


async def create_page(browser: Browser) -> Page:
    """创建带自定义 UA 的上下文并返回新页面。"""
    context = await browser.new_context(user_agent=_UA)
    page = await context.new_page()
    page.set_default_navigation_timeout(_NAVIGATION_TIMEOUT)
    page.set_default_timeout(_NAVIGATION_TIMEOUT)
    return page
