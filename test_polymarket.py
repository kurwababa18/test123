#!/usr/bin/env python3
"""
Quick test script to verify Polymarket API connection.
"""

from core.cache import Cache
from core.polymarket import PolymarketClient

def main():
    print("Testing Polymarket API connection...")
    print("-" * 50)

    # Initialize client
    cache = Cache(max_entries=100)
    client = PolymarketClient(cache)

    # Fetch markets
    print("\nFetching markets...")
    markets = client.get_markets(limit=5)

    if not markets:
        print("❌ No markets fetched! API connection failed.")
        return

    print(f"✅ Successfully fetched {len(markets)} markets!\n")

    # Display first few markets
    for i, market in enumerate(markets[:5], 1):
        parsed = client.parse_market_data(market)
        print(f"\nMarket {i}:")
        print(f"  Title: {parsed['title'][:70]}")
        print(f"  YES: {parsed['yes_price']:.1f}¢")
        print(f"  NO: {parsed['no_price']:.1f}¢")
        print(f"  Volume 24h: ${parsed['volume_24h']:,.2f}")
        print(f"  End Date: {parsed['end_date']}")

    print("\n" + "=" * 50)
    print("✅ Polymarket integration is working!")
    print("=" * 50)

if __name__ == "__main__":
    main()
