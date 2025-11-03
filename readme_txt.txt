========================================
  POLYMARKET TERMINAL
  Real-time Market Monitoring Dashboard
========================================

📋 QUICK START
--------------

1. Double-click run.bat
2. Wait for automatic setup (first run only)
3. Terminal UI will launch automatically

⚙️ REQUIREMENTS
--------------

- Python 3.10 or higher (must be in PATH)
- Internet connection
- Windows OS
- No VPN or proxy required

🎯 FEATURES
-----------

✓ Real-time Polymarket position tracking
✓ Auto-fetch wallet positions from blockchain
✓ Twitter/X monitoring via Nitter
✓ Google News integration
✓ Major outlet RSS feeds
✓ Tabbed interface with custom topics
✓ Smart caching (2 min markets, 30 min feeds)
✓ Auto-retry and rate limit handling
✓ Configurable refresh intervals
✓ Dark theme terminal UI

🎮 KEYBOARD CONTROLS
--------------------

←/→   Switch tabs (wraps around)
R     Refresh data now
+/-   Adjust refresh speed
/     Quick search (shows tab navigation)
E     Edit tab (opens config reminder)
Q     Quit application

📁 FILE STRUCTURE
-----------------

POLYMARKET_TERMINAL\
│
├── run.bat              ← Double-click to start
├── app.py               ← Main application
├── requirements.txt     ← Python dependencies
├── config.yaml          ← Edit to customize topics
├── README.txt           ← This file
│
├── core\                ← Core functionality
│   ├── config.py
│   ├── polymarket.py
│   ├── sources.py
│   ├── cache.py
│   └── log.py
│
├── ui\                  ← User interface
│   └── dashboard.py
│
├── cache\               ← Data cache (auto-created)
├── logs\                ← Log files (auto-created)
└── venv\                ← Python environment (auto-created)

⚙️ CONFIGURATION
----------------

Edit config.yaml to customize:

• wallet_address: Ethereum wallet to monitor
• refresh_seconds: Update interval (5-300 seconds)
• topics: Add/remove/rename tabs
• keywords: Search terms for each topic

Example topic configuration:

topics:
  - key: "my_topic"
    title: "My Custom Topic"
    markets: []
    keywords:
      - "keyword one"
      - "keyword two AND specific"
      - '"exact phrase" OR alternative'

🔧 TROUBLESHOOTING
------------------

Problem: Python not found
Solution: Install Python 3.10+ from python.org
         Add to PATH during installation

Problem: Dependencies won't install
Solution: Run manually:
         venv\Scripts\activate
         pip install -r requirements.txt

Problem: No data showing
Solution: Check internet connection
         Check logs\polyterm.log for errors
         Wait for initial cache to populate

Problem: Rate limited
Solution: App auto-handles this
         Increases intervals automatically
         Rotates through Nitter instances

Problem: Config errors
Solution: Run validation:
         python app.py --check
         Fix any YAML syntax errors

📊 DATA SOURCES
---------------

Polymarket: Gamma API (public, no auth)
  - Wallet positions
  - Market prices & volume
  - End dates

Twitter/X: Nitter RSS (privacy-friendly)
  - Multiple instance fallback
  - Auto-rotation on failures
  - Rate limit handling

Google News: RSS feeds
  - Real-time news search
  - Multiple keywords per topic

Major Outlets: Direct RSS
  - NYT, WaPo, Reuters
  - Politics sections

📝 LOGS
-------

All activity logged to: logs\polyterm.log

- Application events
- Data fetch operations
- Errors and warnings
- Rate limit events

Logs rotate automatically (3 files × 2MB)

🔒 PRIVACY & SAFETY
-------------------

✓ Read-only wallet monitoring (no keys needed)
✓ No data sent to third parties
✓ All processing local
✓ Cache stored locally only
✓ Nitter used for Twitter (no tracking)

⚡ PERFORMANCE TIPS
-------------------

1. Reduce refresh_seconds if rate limited
2. Limit keywords to 5 per topic
3. Cache directory grows to ~200 entries max
4. Clear cache folder if issues occur
5. Monitor logs\polyterm.log for problems

🆘 SUPPORT
----------

Check logs\polyterm.log for detailed errors
Review config.yaml for syntax issues
Ensure Python 3.10+ is installed
Verify internet connectivity

Configuration validation:
  python app.py --check

📄 LICENSE
----------

This software monitors public Polymarket data.
No warranties provided. Use at your own risk.
Respect API rate limits and terms of service.

========================================
Version 1.0 | November 2024
========================================
