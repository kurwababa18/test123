"""
Information panel - shows Twitter trends, news, spikes for a market.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.table import Table as RichTable
from rich.text import Text
from typing import List, Dict, Any

class KeywordActivityPanel(Static):
    """Shows keyword bucket activity and spikes."""

    keyword_stats = reactive({})

    def render(self) -> RichTable:
        table = RichTable(show_header=True, header_style="bold cyan", box=None, title="📊 Keyword Activity")
        table.add_column("Keyword", style="bold", width=30)
        table.add_column("Volume", justify="right", width=10)
        table.add_column("Trend", justify="center", width=8)
        table.add_column("Status", width=15)

        if not self.keyword_stats:
            table.add_row("", "[dim italic]Loading keywords...[/]", "", "")
            return table

        for keyword, stats in self.keyword_stats.items():
            volume = stats.get('count', 0)
            spike_pct = stats.get('spike_percent', 0)

            # Volume display
            vol_str = str(volume) if volume else "-"

            # Trend indicator
            if spike_pct > 100:
                trend = "🔥"
                status = f"[bold red]SPIKE +{spike_pct:.0f}%[/]"
            elif spike_pct > 50:
                trend = "📈"
                status = f"[yellow]Up +{spike_pct:.0f}%[/]"
            elif spike_pct > 0:
                trend = "↗"
                status = f"[green]Rising[/]"
            elif spike_pct < -50:
                trend = "📉"
                status = f"[dim]Down {spike_pct:.0f}%[/]"
            else:
                trend = "→"
                status = "[dim]Stable[/]"

            table.add_row(keyword[:28], vol_str, trend, status)

        return table


class TweetFeedPanel(Static):
    """Shows recent tweets for keyword buckets."""

    tweets = reactive([])

    def render(self) -> RichTable:
        table = RichTable(show_header=True, header_style="bold blue", box=None, title="🐦 Recent Tweets")
        table.add_column("Time", style="dim", width=8)
        table.add_column("Tweet", overflow="fold")

        if not self.tweets:
            table.add_row("", "[dim italic]Loading tweets...[/]")
            return table

        for tweet in self.tweets[:10]:  # Top 10 tweets
            time_str = tweet.get('published', '')[:8] if tweet.get('published') else ''
            title = tweet.get('title', 'No content')

            # Highlight keywords in tweet
            # (simple version - could be enhanced)
            table.add_row(time_str, title[:100])

        return table


class NewsHeadlinePanel(Static):
    """Shows news headlines from multiple sources."""

    headlines = reactive([])

    def render(self) -> RichTable:
        table = RichTable(show_header=True, header_style="bold green", box=None, title="📰 News Headlines")
        table.add_column("Source", style="dim", width=15)
        table.add_column("Headline", overflow="fold")
        table.add_column("Time", style="dim", width=8)

        if not self.headlines:
            table.add_row("", "[dim italic]Loading headlines...[/]", "")
            return table

        for item in self.headlines[:10]:  # Top 10 headlines
            source = item.get('source', 'Unknown')[:13]
            title = item.get('title', 'No title')
            time_str = item.get('published', '')[:8] if item.get('published') else ''

            table.add_row(source, title[:80], time_str)

        return table


class MarketContextPanel(Static):
    """Small context panel showing what market this is about."""

    market_data = reactive({})

    def render(self) -> Text:
        if not self.market_data:
            return Text("Loading market...", style="dim italic")

        title = self.market_data.get('title', 'Unknown Market')

        # Show position info if available
        if 'position' in self.market_data:
            pos = self.market_data['position']
            side = pos.get('side', 'UNKNOWN')
            pnl = pos.get('cash_pnl', 0)

            pnl_color = "green" if pnl >= 0 else "red"
            pnl_str = f"${pnl:.2f}"

            text = Text()
            text.append("📊 ", style="bold")
            text.append(title[:70], style="bold white")
            text.append(f" | Your position: {side} | P&L: ", style="dim")
            text.append(pnl_str, style=f"bold {pnl_color}")
            return text
        else:
            text = Text()
            text.append("📊 ", style="bold")
            text.append(title[:70], style="bold white")
            return text
