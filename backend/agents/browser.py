"""
Enhanced Browser Agent - Multi-tab browsing with intelligent context management
Signature Feature: Advanced browser capabilities beyond standard OpenManus
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
import asyncio


class BrowserTab:
    """Represents a single browser tab with context"""

    def __init__(self, page: Page, tab_id: str, url: str):
        self.page = page
        self.tab_id = tab_id
        self.url = url
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.title: Optional[str] = None
        self.screenshot_path: Optional[str] = None

    async def update_info(self):
        """Update tab information"""
        self.title = await self.page.title()
        self.url = self.page.url
        self.last_accessed = datetime.now()


class EnhancedBrowserAgent:
    """
    Enhanced browser with multi-tab support, context preservation, and intelligent management

    Features:
    - Multi-tab browsing (up to 10 tabs)
    - Automatic tab switching and context management
    - Screenshot capture per tab
    - Session persistence
    - Intelligent resource management
    """

    def __init__(self, max_tabs: int = 10, headless: bool = False):
        self.max_tabs = max_tabs
        self.headless = headless

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.tabs: Dict[str, BrowserTab] = {}
        self.active_tab_id: Optional[str] = None

        self.tab_counter = 0

    async def initialize(self):
        """Initialize the browser"""
        logger.info("🌐 Initializing enhanced browser...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        logger.info("✅ Enhanced browser initialized")

    async def new_tab(self, url: str = "about:blank") -> str:
        """
        Create a new tab

        Args:
            url: Initial URL to navigate to

        Returns:
            Tab ID
        """
        if len(self.tabs) >= self.max_tabs:
            # Close least recently used tab
            await self.close_lru_tab()

        self.tab_counter += 1
        tab_id = f"tab_{self.tab_counter}"

        page = await self.context.new_page()
        if url != "about:blank":
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        tab = BrowserTab(page=page, tab_id=tab_id, url=url)
        await tab.update_info()

        self.tabs[tab_id] = tab
        self.active_tab_id = tab_id

        logger.info(f"📑 New tab created: {tab_id} - {url}")

        return tab_id

    async def switch_tab(self, tab_id: str):
        """Switch to a specific tab"""
        if tab_id not in self.tabs:
            raise ValueError(f"Tab {tab_id} not found")

        self.active_tab_id = tab_id
        self.tabs[tab_id].last_accessed = datetime.now()

        logger.info(f"🔄 Switched to tab: {tab_id}")

    async def close_tab(self, tab_id: str):
        """Close a specific tab"""
        if tab_id not in self.tabs:
            raise ValueError(f"Tab {tab_id} not found")

        tab = self.tabs[tab_id]
        await tab.page.close()
        del self.tabs[tab_id]

        if self.active_tab_id == tab_id:
            self.active_tab_id = next(iter(self.tabs.keys())) if self.tabs else None

        logger.info(f"❌ Closed tab: {tab_id}")

    async def close_lru_tab(self):
        """Close the least recently used tab"""
        if not self.tabs:
            return

        lru_tab_id = min(
            self.tabs.keys(),
            key=lambda tid: self.tabs[tid].last_accessed
        )

        await self.close_tab(lru_tab_id)
        logger.info(f"🗑️ Closed LRU tab: {lru_tab_id}")

    async def get_active_page(self) -> Page:
        """Get the currently active page"""
        if not self.active_tab_id or self.active_tab_id not in self.tabs:
            # Create a new tab if none exists
            await self.new_tab()

        return self.tabs[self.active_tab_id].page

    async def navigate(self, url: str, tab_id: Optional[str] = None):
        """Navigate to URL in specified or active tab"""
        if tab_id:
            await self.switch_tab(tab_id)

        page = await self.get_active_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        if self.active_tab_id:
            await self.tabs[self.active_tab_id].update_info()

        logger.info(f"➡️ Navigated to: {url}")

    async def screenshot(self, tab_id: Optional[str] = None, full_page: bool = False) -> bytes:
        """Take screenshot of specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        screenshot_bytes = await page.screenshot(full_page=full_page)

        logger.info(f"📸 Screenshot captured")

        return screenshot_bytes

    async def execute_script(self, script: str, tab_id: Optional[str] = None) -> Any:
        """Execute JavaScript in specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        result = await page.evaluate(script)
        return result

    async def get_content(self, tab_id: Optional[str] = None) -> str:
        """Get page content from specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        content = await page.content()
        return content

    async def get_text(self, tab_id: Optional[str] = None) -> str:
        """Get visible text from specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        text = await page.evaluate("document.body.innerText")
        return text

    async def click(self, selector: str, tab_id: Optional[str] = None):
        """Click element in specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        await page.click(selector)
        logger.info(f"🖱️ Clicked: {selector}")

    async def type_text(self, selector: str, text: str, tab_id: Optional[str] = None):
        """Type text into element in specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        await page.fill(selector, text)
        logger.info(f"⌨️ Typed into: {selector}")

    async def wait_for_selector(self, selector: str, timeout: int = 5000, tab_id: Optional[str] = None):
        """Wait for selector in specified or active tab"""
        if tab_id:
            page = self.tabs[tab_id].page
        else:
            page = await self.get_active_page()

        await page.wait_for_selector(selector, timeout=timeout)

    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get information about all open tabs"""
        return [
            {
                "tab_id": tab.tab_id,
                "url": tab.url,
                "title": tab.title,
                "created_at": tab.created_at.isoformat(),
                "last_accessed": tab.last_accessed.isoformat(),
                "is_active": tab.tab_id == self.active_tab_id
            }
            for tab in self.tabs.values()
        ]

    async def cleanup(self):
        """Cleanup browser resources"""
        logger.info("🧹 Cleaning up enhanced browser...")

        for tab in list(self.tabs.values()):
            await tab.page.close()

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        logger.info("✅ Browser cleaned up")
