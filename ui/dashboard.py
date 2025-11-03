"""
Textual-based terminal UI for Polymarket Terminal.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, DataTable, TabbedContent, TabPane, Input, Label
from textual.binding import Binding
from textual import work
from textual.reactive import reactive
from rich.text import Text
from rich.table import Table as RichTable
from datetime import datetime
import asyncio
from typing import List, Dict, Any

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

class FeedPanel(Static):
    """Panel displaying news and social media feeds."""
    
    feeds = reactive([])
    
    def render(self) -> RichTable:
        table = RichTable(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Source", style="dim", width=12)
        table.add_column("Headline", overflow="fold")
        
        if not self.feeds:
            table.add_row("", "[dim italic]Loading feeds...[/]")
        else:
            for item in self.feeds[:15]:  # Show top 15
                source = item.get('source', 'Unknown')
                title = item.get('title', 'No title')
                table.add_row(source, title)
        
        return table

class PolymarketApp(App):
    """Main application class."""
    
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
    
    #markets_table {
        height: 60%;
        border: solid $primary;
    }
    
    #feed_panel {
        height: 40%;
        border: solid $accent;
        padding: 0 1;
    }
    
    DataTable {
        height: 100%;
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
        Binding("e", "edit_tab", "Edit Tab", show=False),
        Binding("slash", "search", "Search", show=True),
        Binding("plus", "increase_refresh", "+ Faster", show=False),
        Binding("minus", "decrease_refresh", "- Slower", show=False),
        Binding("q", "quit", "Quit", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.title = "Polymarket Terminal"
        self.config = Config()
        self.cache = Cache(max_entries=self.config.cache_limit)
        self.polymarket = PolymarketClient(
            self.cache,
            api_key=self.config.polymarket_api_key,
            api_secret=self.config.polymarket_api_secret,
            api_passphrase=self.config.polymarket_api_passphrase
        )
        self.feeds = FeedSource(self.cache, self.config.nitter_urls)
        
        self.current_tab_idx = 0
        self.topics = self.config.topics
        self.last_update = None
        self.refresh_task = None
        self.markets_data = {}
        self.feeds_data = {}
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield StatusBar(id="status_bar")
        
        with Container(id="main_container"):
            with TabbedContent(id="tabs"):
                for topic in self.topics:
                    with TabPane(topic['title'], id=topic['key']):
                        yield DataTable(id=f"table_{topic['key']}")
                        yield FeedPanel(id=f"feeds_{topic['key']}")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Setup data tables
        for topic in self.topics:
            table_id = f"table_{topic['key']}"
            table = self.query_one(f"#{table_id}", DataTable)
            table.add_columns("Market", "YES¢", "NO¢", "24h Vol", "Ends")
            table.cursor_type = "row"
        
        # Start refresh loop
        self.refresh_data()
        self.set_interval(self.config.refresh_seconds, self.refresh_data)
        
        logger.info("Application started")
    
    @work(exclusive=True)
    async def refresh_data(self):
        """Refresh all data from sources - fetches wallet positions and updates UI."""
        try:
            status = self.query_one("#status_bar", StatusBar)
            status.status_text = "🔄 Fetching your positions..."

            # Fetch wallet positions
            positions = await asyncio.to_thread(
                self.polymarket.get_wallet_positions,
                self.config.wallet_address
            )

            if not positions:
                # No positions found - use config topics as fallback
                logger.warning("No positions found, using config topics")
                status.status_text = "⚠️  No positions found - using default topics"
                # Fall back to config topics
                self.topics = self.config.topics
            else:
                # Generate dynamic topics from user's positions
                dynamic_topics = await asyncio.to_thread(
                    self.polymarket.generate_topics_from_positions,
                    positions
                )

                if dynamic_topics:
                    self.topics = dynamic_topics
                    logger.info(f"Using {len(dynamic_topics)} dynamic topics from positions")

            # Update each topic
            for topic in self.topics:
                topic_key = topic['key']

                # Update markets table - show the market(s) for this topic
                try:
                    table = self.query_one(f"#table_{topic_key}", DataTable)
                    table.clear()

                    display_markets = topic.get('markets', [])

                    for market_data in display_markets:
                        parsed = market_data if isinstance(market_data, dict) and 'title' in market_data else self.polymarket.parse_market_data(market_data)

                        title = parsed['title'][:50]
                        yes_price = f"{parsed['yes_price']:.1f}¢"
                        no_price = f"{parsed['no_price']:.1f}¢"

                        # Show position info if available
                        if 'position' in parsed:
                            pos = parsed['position']
                            pnl = f"P/L: ${pos['cash_pnl']:.2f}"
                            side = f"({pos['side']})"
                            table.add_row(f"{title} {side}", yes_price, no_price, pnl, parsed['end_date'][:10] if parsed['end_date'] != 'N/A' else 'N/A')
                        else:
                            volume = f"${parsed['volume_24h']/1000:.1f}K"
                            table.add_row(title, yes_price, no_price, volume, parsed['end_date'][:10] if parsed['end_date'] != 'N/A' else 'N/A')

                    self.markets_data[topic_key] = display_markets
                except Exception as e:
                    logger.warning(f"Could not update table for topic {topic_key}: {e}")

                # Update feeds with keywords from this topic
                keywords = topic.get('keywords', [])
                if keywords:
                    try:
                        feed_items = await asyncio.to_thread(
                            self.feeds.aggregate_feeds,
                            keywords
                        )

                        feed_panel = self.query_one(f"#feeds_{topic_key}", FeedPanel)
                        feed_panel.feeds = feed_items
                        self.feeds_data[topic_key] = feed_items
                    except Exception as e:
                        logger.warning(f"Could not update feeds for topic {topic_key}: {e}")

            # Update status
            self.last_update = datetime.now()
            position_count = len(positions) if positions else 0
            status.status_text = (
                f"✅ Updated {self.last_update.strftime('%H:%M:%S')} | "
                f"{position_count} positions | "
                f"Next: {self.config.refresh_seconds}s"
            )

            logger.info(f"Data refresh complete: {position_count} positions")

        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            logger.exception(e)
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
    
    def action_increase_refresh(self) -> None:
        """Decrease refresh interval (faster)."""
        current = self.config.refresh_seconds
        new_value = max(5, current - 5)
        self.config.refresh_seconds = new_value
        
        status = self.query_one("#status_bar", StatusBar)
        status.status_text = f"⏱️  Refresh interval: {new_value}s"
        
        # Restart interval
        self.set_interval(new_value, self.refresh_data)
    
    def action_decrease_refresh(self) -> None:
        """Increase refresh interval (slower)."""
        current = self.config.refresh_seconds
        new_value = min(300, current + 5)
        self.config.refresh_seconds = new_value
        
        status = self.query_one("#status_bar", StatusBar)
        status.status_text = f"⏱️  Refresh interval: {new_value}s"
        
        # Restart interval
        self.set_interval(new_value, self.refresh_data)
    
    def action_search(self) -> None:
        """Open search dialog."""
        # Simple notification for now
        status = self.query_one("#status_bar", StatusBar)
        status.status_text = "🔍 Search: Use ← → to navigate tabs"
    
    def action_edit_tab(self) -> None:
        """Edit current tab (rename/delete)."""
        status = self.query_one("#status_bar", StatusBar)
        status.status_text = "✏️  Edit: Feature coming soon (edit config.yaml)"
    
    def on_unmount(self) -> None:
        """Cleanup when app closes."""
        self.polymarket.close()
        self.feeds.close()
        logger.info("Application closed")
