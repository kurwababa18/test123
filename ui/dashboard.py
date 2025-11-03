"""
Textual-based terminal UI for Polymarket Terminal.
Displays information aggregation (Twitter trends, news, spikes) for wallet positions.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane, Label, Rule
from textual.binding import Binding
from textual import work
from textual.reactive import reactive
from rich.text import Text
from rich.table import Table as RichTable
from rich.panel import Panel
from datetime import datetime
import asyncio
from typing import List, Dict, Any
from collections import Counter

from core.config import Config
from core.cache import Cache
from core.polymarket import PolymarketClient
from core.sources import FeedSource
from core.log import get_logger

logger = get_logger(__name__)

class StatusBar(Static):
    """Status bar showing last update and stats."""

    status_text = reactive("")

    def render(self) -> str:
        return self.status_text

class KeywordBucketPanel(Static):
    """Displays keyword buckets with trend indicators and spike detection."""

    keywords = reactive([])
    trends = reactive({})

    def render(self) -> RichTable:
        table = RichTable(show_header=True, header_style="bold cyan", box=None, expand=True)
        table.add_column("Keyword", style="bold", width=30)
        table.add_column("Mentions", justify="right", width=10)
        table.add_column("Trend", justify="center", width=10)

        if not self.keywords:
            table.add_row("[dim italic]No keywords configured[/]", "", "")
            table.add_row("[dim]Edit config.yaml to add keywords[/]", "", "")
        else:
            for keyword in self.keywords[:15]:  # Show top 15
                mention_count = self.trends.get(keyword, 0)

                # Simple spike indicator (can be enhanced later)
                if mention_count > 50:
                    trend = "[bold red]🔥 SPIKE[/]"
                elif mention_count > 20:
                    trend = "[yellow]📈 High[/]"
                elif mention_count > 0:
                    trend = "[green]→ Active[/]"
                else:
                    trend = "[dim]— Quiet[/]"

                table.add_row(
                    keyword[:30],
                    str(mention_count) if mention_count > 0 else "[dim]0[/]",
                    trend
                )

        return table

class InformationPanel(Static):
    """Panel displaying aggregated information (Twitter, news, RSS)."""

    feeds = reactive([])

    def render(self) -> RichTable:
        table = RichTable(show_header=True, header_style="bold magenta", box=None, expand=True)
        table.add_column("Source", style="dim", width=12)
        table.add_column("Headline/Tweet", overflow="fold")
        table.add_column("Time", style="dim", width=10)

        if not self.feeds:
            table.add_row("", "[dim italic]Loading information...[/]", "")
        else:
            for item in self.feeds[:20]:  # Show top 20
                source = item.get('source', 'Unknown')[:12]
                title = item.get('title', 'No title')
                pub_date = item.get('published', '')

                # Format time
                try:
                    if pub_date:
                        dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M')
                    else:
                        time_str = ""
                except:
                    time_str = ""

                table.add_row(source, title, time_str)

        return table

class PolymarketApp(App):
    """Main application class - information aggregator for wallet positions."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
        height: 1;
    }

    Footer {
        background: $panel;
        color: $text;
        height: 1;
    }

    #status_bar {
        dock: top;
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
    }

    #main_container {
        height: 100%;
    }

    .market_context {
        height: auto;
        padding: 0 1;
        background: $panel;
        color: $text;
    }

    #keyword_panel {
        height: 40%;
        border: solid $primary;
        padding: 1;
    }

    #info_panel {
        height: 60%;
        border: solid $accent;
        padding: 1;
    }

    .search_input {
        dock: top;
        height: 3;
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("left", "prev_tab", "← Prev Tab", show=True),
        Binding("right", "next_tab", "→ Next Tab", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("e", "edit_keywords", "Edit Keywords", show=False),
        Binding("slash", "search", "Search", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.title = "Polymarket Information Terminal"
        self.config = Config()
        self.cache = Cache(max_entries=self.config.cache_limit)
        self.polymarket = PolymarketClient(self.cache)
        self.feeds = FeedSource(self.cache, self.config.nitter_urls)

        self.positions = []
        self.last_update = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield StatusBar(id="status_bar")

        with Container(id="main_container"):
            with TabbedContent(id="tabs"):
                # Tabs will be generated dynamically from wallet positions
                yield TabPane("Loading...", id="loading_pane")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Fetch positions and build tabs
        self.initialize_tabs()

        # Start refresh loop
        self.set_interval(self.config.refresh_seconds, self.refresh_data)

        logger.info("Application started - information aggregation mode")

    @work(exclusive=True, thread=True)
    async def initialize_tabs(self):
        """Fetch wallet positions and create tabs dynamically."""
        try:
            status = self.query_one("#status_bar", StatusBar)
            status.status_text = "🔄 Loading your positions..."

            # Fetch positions from wallet
            positions = await asyncio.to_thread(
                self.polymarket.get_wallet_positions,
                self.config.wallet_address
            )

            if not positions:
                logger.warning("No positions found")
                status.status_text = "⚠️  No positions found - check wallet address in config.yaml"
                return

            self.positions = positions
            logger.info(f"Found {len(positions)} positions")

            # Sync positions with config (auto-generate keywords)
            await asyncio.to_thread(
                self.config.sync_markets,
                positions,
                self.polymarket.extract_keywords
            )

            # Rebuild tabs from positions
            tabs_container = self.query_one(TabbedContent)

            # Clear loading pane
            await tabs_container.remove_children()

            # Create tab for each position
            for position in positions:
                slug = position.get('slug', '')
                title = position.get('question', position.get('title', 'Unknown Market'))

                if not slug:
                    continue

                # Shorten title for tab
                tab_title = title[:40] + "..." if len(title) > 40 else title

                with tabs_container.compose():
                    with TabPane(tab_title, id=f"tab_{slug}"):
                        # Market context (minimal)
                        market_label = Label(
                            f"[bold cyan]Market:[/] {title}",
                            classes="market_context"
                        )
                        yield market_label
                        yield Rule()

                        # Keyword buckets with trend tracking
                        yield KeywordBucketPanel(id=f"keywords_{slug}")

                        # Information aggregation panel
                        yield InformationPanel(id=f"info_{slug}")

            # Trigger first data refresh
            self.refresh_data()

            status.status_text = f"✅ Loaded {len(positions)} markets - aggregating information..."

        except Exception as e:
            logger.error(f"Error initializing tabs: {e}")
            status = self.query_one("#status_bar", StatusBar)
            status.status_text = f"❌ Error: {str(e)[:50]}"

    @work(exclusive=True, thread=True)
    async def refresh_data(self):
        """Refresh information aggregation for all markets."""
        try:
            if not self.positions:
                return

            status = self.query_one("#status_bar", StatusBar)
            status.status_text = "🔄 Aggregating information..."

            # Update each market tab
            for position in self.positions:
                slug = position.get('slug', '')
                title = position.get('question', position.get('title', ''))

                if not slug:
                    continue

                # Get configured keywords for this market
                keywords = self.config.get_market_keywords(slug)

                if not keywords:
                    # No keywords configured yet - skip
                    continue

                # Update keyword panel
                try:
                    keyword_panel = self.query_one(f"#keywords_{slug}", KeywordBucketPanel)
                    keyword_panel.keywords = keywords

                    # Fetch trend data (mention counts from feeds)
                    feed_items = await asyncio.to_thread(
                        self.feeds.aggregate_feeds,
                        keywords
                    )

                    # Calculate mention counts per keyword
                    trends = {}
                    for keyword in keywords:
                        count = sum(1 for item in feed_items
                                  if keyword.lower() in item.get('title', '').lower())
                        trends[keyword] = count

                    keyword_panel.trends = trends

                    # Update information panel
                    info_panel = self.query_one(f"#info_{slug}", InformationPanel)
                    info_panel.feeds = feed_items

                except Exception as e:
                    logger.error(f"Error updating tab {slug}: {e}")
                    continue

            # Update status
            self.last_update = datetime.now()
            status.status_text = (
                f"✅ Updated {self.last_update.strftime('%H:%M:%S')} | "
                f"{len(self.positions)} markets | "
                f"Next: {self.config.refresh_seconds}s"
            )

            logger.info(f"Information refresh complete: {len(self.positions)} markets")

        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            status = self.query_one("#status_bar", StatusBar)
            status.status_text = f"❌ Error: {str(e)[:50]}"

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabs = self.query_one(TabbedContent)
        current = tabs.active
        tab_ids = [pane.id for pane in tabs.query(TabPane)]

        if current in tab_ids:
            idx = tab_ids.index(current)
            prev_idx = (idx - 1) % len(tab_ids)
            tabs.active = tab_ids[prev_idx]

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one(TabbedContent)
        current = tabs.active
        tab_ids = [pane.id for pane in tabs.query(TabPane)]

        if current in tab_ids:
            idx = tab_ids.index(current)
            next_idx = (idx + 1) % len(tab_ids)
            tabs.active = tab_ids[next_idx]

    def action_refresh(self) -> None:
        """Manually trigger refresh."""
        self.refresh_data()

    def action_search(self) -> None:
        """Open search dialog."""
        status = self.query_one("#status_bar", StatusBar)
        status.status_text = "🔍 Search: Use ← → to navigate tabs"

    def action_edit_keywords(self) -> None:
        """Edit keyword buckets for current market."""
        status = self.query_one("#status_bar", StatusBar)
        status.status_text = "✏️  Edit keywords in config.yaml (auto-reloads)"

    def on_unmount(self) -> None:
        """Cleanup when app closes."""
        self.polymarket.close()
        self.feeds.close()
        logger.info("Application closed")
