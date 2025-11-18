"""
Enhanced Browser Agent - Multi-tab browsing with intelligent context management
Signature Features:
- Advanced browser capabilities beyond standard OpenManus
- Session persistence and restoration
- Cookie and storage management
- Automatic state saving
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
import asyncio
import json
from pathlib import Path


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
    - Session persistence and restoration
    - Cookie and storage management
    - Automatic state saving
    - Intelligent resource management
    """

    def __init__(
        self,
        max_tabs: int = 10,
        headless: bool = False,
        session_id: Optional[str] = None,
        persist_sessions: bool = True
    ):
        self.max_tabs = max_tabs
        self.headless = headless
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.persist_sessions = persist_sessions

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.tabs: Dict[str, BrowserTab] = {}
        self.active_tab_id: Optional[str] = None

        self.tab_counter = 0

        # Session persistence
        self.session_dir = Path("./data/browser_sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / f"{self.session_id}.json"

        # Auto-save interval (seconds)
        self.auto_save_interval = 60
        self.auto_save_task: Optional[asyncio.Task] = None

    async def initialize(self, restore_session: bool = True):
        """
        Initialize the browser

        Args:
            restore_session: Whether to restore previous session if available
        """
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

        # Restore previous session if requested
        if restore_session and self.session_file.exists():
            await self.restore_session()

        # Start auto-save if persistence enabled
        if self.persist_sessions:
            self.auto_save_task = asyncio.create_task(self._auto_save_loop())
            logger.info(f"💾 Auto-save enabled (interval: {self.auto_save_interval}s)")

    async def save_session(self) -> Dict[str, Any]:
        """
        Save current browser session to disk

        Returns:
            Session data
        """
        session_data = {
            "session_id": self.session_id,
            "saved_at": datetime.now().isoformat(),
            "max_tabs": self.max_tabs,
            "active_tab_id": self.active_tab_id,
            "tab_counter": self.tab_counter,
            "tabs": []
        }

        # Save tab information
        for tab_id, tab in self.tabs.items():
            tab_data = {
                "tab_id": tab_id,
                "url": tab.url,
                "title": tab.title,
                "created_at": tab.created_at.isoformat(),
                "last_accessed": tab.last_accessed.isoformat()
            }
            session_data["tabs"].append(tab_data)

        # Save cookies from context
        if self.context:
            cookies = await self.context.cookies()
            session_data["cookies"] = cookies

        # Save to file
        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"💾 Session saved: {self.session_id} ({len(self.tabs)} tabs)")

        return session_data

    async def restore_session(self) -> bool:
        """
        Restore browser session from disk

        Returns:
            True if successful, False otherwise
        """
        if not self.session_file.exists():
            logger.warning(f"No saved session found: {self.session_id}")
            return False

        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)

            logger.info(f"📂 Restoring session: {session_data['session_id']} from {session_data['saved_at']}")

            # Restore cookies
            if "cookies" in session_data and self.context:
                await self.context.add_cookies(session_data["cookies"])
                logger.info(f"🍪 Restored {len(session_data['cookies'])} cookies")

            # Restore tabs
            for tab_data in session_data.get("tabs", []):
                try:
                    # Create new tab with saved URL
                    tab_id = await self.new_tab(url=tab_data["url"])

                    # Restore metadata
                    tab = self.tabs[tab_id]
                    tab.tab_id = tab_data["tab_id"]  # Use original tab_id
                    tab.title = tab_data.get("title")
                    tab.created_at = datetime.fromisoformat(tab_data["created_at"])
                    tab.last_accessed = datetime.fromisoformat(tab_data["last_accessed"])

                    # Update tabs dict with original tab_id
                    if tab_id != tab_data["tab_id"]:
                        self.tabs[tab_data["tab_id"]] = tab
                        del self.tabs[tab_id]

                    logger.info(f"📑 Restored tab: {tab_data['tab_id']} - {tab_data['url']}")

                except Exception as e:
                    logger.error(f"Failed to restore tab {tab_data['tab_id']}: {e}")

            # Restore active tab
            if session_data.get("active_tab_id") and session_data["active_tab_id"] in self.tabs:
                self.active_tab_id = session_data["active_tab_id"]

            # Restore counter
            self.tab_counter = session_data.get("tab_counter", self.tab_counter)

            logger.info(f"✅ Session restored: {len(self.tabs)} tabs")

            return True

        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
            return False

    async def _auto_save_loop(self):
        """Automatic session saving loop"""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)

                if self.tabs:  # Only save if there are tabs
                    await self.save_session()

            except asyncio.CancelledError:
                # Save one last time before exiting
                if self.tabs:
                    await self.save_session()
                break
            except Exception as e:
                logger.error(f"Auto-save error: {e}")

    async def clear_session(self):
        """Clear saved session data"""
        if self.session_file.exists():
            self.session_file.unlink()
            logger.info(f"🗑️ Cleared session: {self.session_id}")

    @classmethod
    async def list_saved_sessions(cls, session_dir: str = "./data/browser_sessions") -> List[Dict[str, Any]]:
        """
        List all saved browser sessions

        Returns:
            List of session information
        """
        session_path = Path(session_dir)
        if not session_path.exists():
            return []

        sessions = []

        for session_file in session_path.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)

                sessions.append({
                    "session_id": session_data["session_id"],
                    "saved_at": session_data["saved_at"],
                    "num_tabs": len(session_data.get("tabs", [])),
                    "file": str(session_file)
                })

            except Exception as e:
                logger.error(f"Failed to read session file {session_file}: {e}")

        return sessions

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

    async def cleanup(self, save_session: bool = True):
        """
        Cleanup browser resources

        Args:
            save_session: Whether to save session before cleanup
        """
        logger.info("🧹 Cleaning up enhanced browser...")

        # Stop auto-save task
        if self.auto_save_task:
            self.auto_save_task.cancel()
            try:
                await self.auto_save_task
            except asyncio.CancelledError:
                pass

        # Save session if requested
        if save_session and self.persist_sessions and self.tabs:
            await self.save_session()

        # Close all tabs
        for tab in list(self.tabs.values()):
            await tab.page.close()

        # Close browser context and browser
        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        logger.info("✅ Browser cleaned up")
