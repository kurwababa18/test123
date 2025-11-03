"""
Polymarket Terminal - Main Entry Point
Fetches Polymarket positions, Twitter/X feeds, and news for monitoring markets.
"""

import sys
import os
from pathlib import Path

# Ensure we're in the right directory
APP_ROOT = Path(__file__).parent.absolute()
os.chdir(APP_ROOT)

# Add core and ui to path
sys.path.insert(0, str(APP_ROOT / "core"))
sys.path.insert(0, str(APP_ROOT / "ui"))

def check_dependencies():
    """Check if all required packages are installed."""
    required = [
        'textual', 'rich', 'httpx', 'yaml', 
        'feedparser', 'dateutil', 'colorama'
    ]
    missing = []
    
    for pkg in required:
        try:
            if pkg == 'yaml':
                __import__('yaml')
            elif pkg == 'dateutil':
                __import__('dateutil')
            else:
                __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Installing dependencies...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed. Please restart the application.")
        sys.exit(0)

def setup_environment():
    """Create necessary directories and config if they don't exist."""
    # Create directories
    (APP_ROOT / "cache").mkdir(exist_ok=True)
    (APP_ROOT / "logs").mkdir(exist_ok=True)
    (APP_ROOT / "core").mkdir(exist_ok=True)
    (APP_ROOT / "ui").mkdir(exist_ok=True)
    
    # Create config if missing
    config_path = APP_ROOT / "config.yaml"
    if not config_path.exists():
        print("⚠️  config.yaml not found. Creating default configuration...")
        default_config = """# Polymarket Terminal Configuration

wallet_address: "0x165Ab23404f12a077c45426a36EDCE442347B477"
refresh_seconds: 15
cache_limit: 200
cache_ttl_markets: 120  # 2 minutes
cache_ttl_feeds: 1800   # 30 minutes

nitter:
  base_urls:
    - "https://nitter.net"
    - "https://nitter.it"
    - "https://nitter.poast.org"
  fallback_on_error: true

topics:
  - key: "venezuela_conflict"
    title: "US–Venezuela"
    markets: []
    keywords:
      - "Venezuela AND Pentagon"
      - "Venezuela AND Southern Command"
      - "Trump AND Maduro"
      - "Nicolás Maduro OR Maduro"
      - "Caracas AND (troops OR military OR strike)"
      - "Venezuela AND (incursion OR border OR use of force)"
  
  - key: "gov_shutdown"
    title: "Government Shutdown"
    markets: []
    keywords:
      - "government shutdown"
      - "continuing resolution OR CR vote"
      - "House Rules Committee AND (CR OR spending)"
      - "Schumer AND (shutdown OR CR)"
      - "OMB OR CBO AND (score OR estimate)"
"""
        config_path.write_text(default_config, encoding='utf-8')
        print("✅ Default config.yaml created.")

def main():
    """Main entry point."""
    if '--check' in sys.argv:
        # Config validation mode
        from core.config import Config
        from core.log import setup_logging
        
        setup_logging()
        config = Config()
        print(f"✅ Configuration valid!")
        print(f"   Wallet: {config.wallet_address}")
        print(f"   Refresh: {config.refresh_seconds}s")
        print(f"   Topics: {len(config.topics)}")
        for topic in config.topics:
            print(f"     - {topic['title']} ({len(topic['keywords'])} keywords)")
        return
    
    # Normal startup
    print("🚀 Polymarket Terminal Starting...")
    check_dependencies()
    setup_environment()
    
    # Import after dependencies are checked
    from ui.dashboard import PolymarketApp
    from core.log import setup_logging
    
    setup_logging()
    
    try:
        app = PolymarketApp()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
