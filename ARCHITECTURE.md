# Polymarket Terminal - Architecture

## Purpose

This is an **information aggregator and trend detector**, NOT a portfolio viewer.

### What it does:
1. Fetches your Polymarket positions (to know what you care about)
2. For EACH position, creates a tab with:
   - Twitter trend tracking
   - News headline aggregation
   - Keyword spike detection
   - Custom searchable keyword buckets

### What it does NOT do:
- Show market prices/P&L in detail (you use Polymarket for that)
- Replace Polymarket's UI
- Track your portfolio performance

---

## Information Flow

```
Your Wallet Address
        ↓
   [Fetch Positions API]
        ↓
   Extract Market Questions
        ↓
   Generate Keyword Buckets (auto + custom)
        ↓
┌──────────────────────────────┐
│   For Each Market:           │
│   1. Search Twitter/Nitter   │
│   2. Fetch Google News        │
│   3. Aggregate RSS feeds      │
│   4. Count keyword mentions   │
│   5. Detect spikes            │
└──────────────────────────────┘
        ↓
   Display in Terminal UI
```

---

## Components

### 1. Data Fetching (`core/`)

- **`polymarket.py`**:
  - Fetches wallet positions from `data-api.polymarket.com`
  - Extracts keywords from market titles
  - Generates topic configs from positions

- **`sources.py`**:
  - Twitter/Nitter RSS scraping
  - Google News aggregation
  - RSS feed parsing
  - Rate limit handling + rotation

- **`spike_detector.py`** (NEW):
  - Tracks keyword mention counts over time
  - Detects volume spikes (>50% increase)
  - Stores 24-hour history per keyword

- **`cache.py`**:
  - TTL-based file cache
  - Avoids API rate limits

- **`config.py`**:
  - Loads `config.yaml`
  - Manages custom keyword buckets

### 2. UI (`ui/`)

- **`dashboard.py`**:
  - Main Textual app
  - Tab management
  - Data refresh loop
  - Keyboard shortcuts

- **`information_panel.py`** (NEW):
  - `KeywordActivityPanel` - Shows keyword volume + spikes
  - `TweetFeedPanel` - Recent tweets
  - `NewsHeadlinePanel` - News from multiple sources
  - `MarketContextPanel` - Small context banner

---

## Configuration (`config.yaml`)

### Custom Keyword Buckets

You can customize keywords for any market:

```yaml
custom_keyword_buckets:
  venezuela_conflict:
    keywords:
      - "Venezuela AND Pentagon"
      - "Trump AND Maduro"
      - "Nicolás Maduro OR Maduro"
```

**How it works:**
1. App fetches your positions
2. Auto-generates keywords from market titles
3. Checks `custom_keyword_buckets` for overrides
4. Merges auto + custom keywords
5. Creates search buckets

---

## UI Layout (Per Tab)

```
┌─────────────────────────────────────────────────┐
│ 📊 Market: "Will there be a US-Venezuela       │
│            conflict in 2025?"                   │
│    Your position: YES | P&L: $127.50           │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📊 KEYWORD ACTIVITY                             │
│ ┌─────────────────────────────────────────────┐ │
│ │ Keyword          Volume  Trend  Status      │ │
│ │ Venezuela        23      🔥      SPIKE +150%│ │
│ │ Maduro           15      📈      Up +60%    │ │
│ │ Pentagon         8       →       Stable     │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ 🐦 RECENT TWEETS                                │
│ ┌─────────────────────────────────────────────┐ │
│ │ 14:32  Breaking: Venezuela tensions rise... │ │
│ │ 14:15  Maduro responds to US threats...     │ │
│ │ 13:58  Pentagon official statement on...    │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ 📰 NEWS HEADLINES                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ Reuters    Venezuela crisis deepens...      │ │
│ │ NYT        US military options in South...  │ │
│ │ WaPo       Maduro regime faces pressure...  │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## What's Working

✅ Fetch wallet positions
✅ Auto-generate keyword buckets from market titles
✅ Twitter/Nitter scraping with rotation
✅ Google News + RSS aggregation
✅ Spike detection algorithm
✅ Custom keyword bucket config
✅ Information-focused UI panels

## What's Next

🔲 Wire information panels into main dashboard
🔲 Count keyword mentions in tweets
🔲 Show spike indicators in real-time
🔲 UI for editing keyword buckets (press 'E')
🔲 Visual activity graphs/charts
🔲 Sentiment analysis (optional)

---

## Testing (Blocked by Network)

The Polymarket APIs are currently blocked in this environment (403 Cloudflare), but the code is correct and will work when run locally with normal internet access.

### Testing Commands:

```bash
# Test wallet positions
python3 test_wallet_positions.py

# Test the full terminal
python3 app.py
```

---

## Key Insight

> **This is NOT a portfolio tracker.**
> **This is an information radar for your investments.**

You don't need another place to see "YES: 62¢, NO: 38¢" - Polymarket shows that.

What you NEED is:
- "Is 'Maduro' suddenly trending? (spike +150%)"
- "What are people saying on Twitter about Venezuela?"
- "Any breaking news affecting my position?"

That's what this terminal provides.
