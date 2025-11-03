#!/usr/bin/env python3
"""
Test script to verify Polymarket wallet position fetching.
"""

from core.cache import Cache
from core.polymarket import PolymarketClient
from core.config import Config

def main():
    print("Testing Polymarket Wallet Position Fetching...")
    print("=" * 70)

    # Load config to get wallet address
    config = Config()
    wallet_address = config.wallet_address

    print(f"\nWallet Address: {wallet_address}")
    print("-" * 70)

    # Initialize client
    cache = Cache(max_entries=100)
    client = PolymarketClient(cache)

    # Fetch wallet positions
    print("\nFetching your wallet positions...")
    positions = client.get_wallet_positions(wallet_address)

    if not positions:
        print("❌ No positions found or API connection failed!")
        print("\nThis could mean:")
        print("  1. You don't have any open positions")
        print("  2. API is blocked by network restrictions")
        print("  3. Wallet address is incorrect")
        return

    print(f"✅ Successfully fetched {len(positions)} positions!\n")

    # Display positions
    total_value = 0
    total_pnl = 0

    for i, position in enumerate(positions[:10], 1):  # Show top 10
        parsed = client.parse_market_data(position)

        print(f"\nPosition {i}:")
        print(f"  Market: {parsed['title'][:65]}")

        if 'position' in parsed:
            pos = parsed['position']
            print(f"  Side: {pos['side']}")
            print(f"  Size: {pos['size']:.4f} shares")
            print(f"  Current Value: ${pos['current_value']:.2f}")
            print(f"  Cash P&L: ${pos['cash_pnl']:.2f} ({pos['percent_pnl']:.1f}%)")
            total_value += pos['current_value']
            total_pnl += pos['cash_pnl']
        else:
            print(f"  YES: {parsed['yes_price']:.1f}¢")
            print(f"  NO: {parsed['no_price']:.1f}¢")

        print(f"  End Date: {parsed['end_date']}")

    print("\n" + "=" * 70)
    print(f"Total Portfolio Value: ${total_value:.2f}")
    print(f"Total Cash P&L: ${total_pnl:.2f}")
    print("=" * 70)
    print("✅ Wallet position fetching is working!")

if __name__ == "__main__":
    main()
