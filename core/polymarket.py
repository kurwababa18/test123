"""
Polymarket API client for fetching market data using Gamma API.
"""

import httpx
from typing import List, Dict, Any, Optional
from core.log import get_logger
from core.cache import Cache

logger = get_logger(__name__)

class PolymarketClient:
    """Client for Polymarket Gamma API."""

    GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"

    def __init__(self, cache: Cache, api_key: Optional[str] = None, api_secret: Optional[str] = None, api_passphrase: Optional[str] = None):
        """
        Initialize Polymarket client.

        Args:
            cache: Cache instance for storing API responses
            api_key: Optional API key (not used for Gamma API)
            api_secret: Optional API secret (not used for Gamma API)
            api_passphrase: Optional API passphrase (not used for Gamma API)
        """
        self.cache = cache
        # Use trust_env=True to respect HTTP_PROXY/HTTPS_PROXY environment variables
        self.client = httpx.Client(timeout=30.0, trust_env=True)

        # Gamma API doesn't require authentication for read-only access
        logger.info("Using Polymarket Gamma API (read-only, no authentication required)")

    def get_markets(self, limit: int = 100, active: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch active markets from Polymarket Gamma API.

        Args:
            limit: Maximum number of markets to return (default 100)
            active: Only return active markets (default True)

        Returns:
            List of market data dictionaries
        """
        cache_key = f"markets_gamma_{limit}_{active}"

        # Try cache first
        cached = self.cache.get(cache_key, ttl=120)  # 2 min TTL
        if cached is not None:
            logger.info(f"Using cached markets ({len(cached)} markets)")
            return cached

        try:
            logger.info(f"Fetching markets from Polymarket Gamma API...")

            # Prepare query parameters (matching official Polymarket agents implementation)
            params = {
                "limit": limit,
                "active": active,
                "closed": False,
                "archived": False
            }

            # Make the request with headers
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; PolymarketTerminal/1.0)"
            }
            response = self.client.get(self.GAMMA_MARKETS_URL, params=params, headers=headers)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            markets = []

            # Handle different response formats
            if isinstance(data, list):
                markets = data
            elif isinstance(data, dict):
                # Try common keys
                if 'data' in data:
                    markets = data['data']
                elif 'markets' in data:
                    markets = data['markets']
                else:
                    # If the dict itself is a single market, wrap it
                    markets = [data]

            logger.info(f"Fetched {len(markets)} markets from Polymarket Gamma API")

            # Cache the result
            self.cache.set(cache_key, markets)

            return markets

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching markets: {e.response.status_code} - {e.response.text[:200]}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching markets: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            logger.exception(e)
            return []

    def get_wallet_positions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Fetch open positions for a wallet.

        Note: The Gamma API doesn't support wallet-specific filtering.
        Returns general market data instead.

        Args:
            wallet_address: Ethereum wallet address (not used)

        Returns:
            List of market data dictionaries
        """
        logger.info("Wallet-specific positions not available via Gamma API. Returning general markets.")
        return self.get_markets(limit=100)

    def get_market_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific market by slug.

        Args:
            slug: Market slug identifier

        Returns:
            Market data dictionary or None
        """
        cache_key = f"market_{slug}"

        # Try cache first
        cached = self.cache.get(cache_key, ttl=120)
        if cached is not None:
            return cached

        try:
            logger.info(f"Fetching market by slug: {slug}")

            # The Gamma API doesn't have a direct slug endpoint
            # We need to search through markets
            markets = self.get_markets(limit=1000, active=True)

            for market in markets:
                # Check various slug/ID fields
                market_slug = market.get('slug', '')
                condition_id = market.get('conditionId', '')
                question_id = market.get('questionID', '')

                if slug in [market_slug, condition_id, question_id]:
                    # Cache the result
                    self.cache.set(cache_key, market)
                    return market

            logger.warning(f"Market not found: {slug}")
            return None

        except Exception as e:
            logger.error(f"Error fetching market {slug}: {e}")
            return None

    def parse_market_data(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse market data into standardized format.

        Args:
            market: Raw market data from Gamma API

        Returns:
            Parsed market data with keys: title, yes_price, no_price, volume_24h, end_date
        """
        try:
            # Handle both dict and string responses
            if isinstance(market, str):
                logger.warning(f"Market data is string, skipping: {market[:100]}")
                return self._get_empty_market()

            if not isinstance(market, dict):
                logger.warning(f"Market data is not dict, skipping: {type(market)}")
                return self._get_empty_market()

            # Extract title/question - Gamma API uses 'question' field
            title = (
                market.get('question') or
                market.get('title') or
                market.get('description') or
                'Unknown Market'
            )

            # Parse outcomes - Gamma API structure
            outcomes = market.get('outcomes', [])
            tokens = market.get('tokens', [])
            clob_token_ids = market.get('clobTokenIds', [])

            yes_price = 0.0
            no_price = 0.0

            # Method 1: Try outcomes array (most common in Gamma API)
            if outcomes and isinstance(outcomes, list) and len(outcomes) >= 2:
                # Gamma API typically has outcomes in order
                # First outcome is usually YES, second is NO
                # But we should check the text to be sure
                for outcome in outcomes:
                    if isinstance(outcome, str):
                        outcome_text = outcome.upper()
                        # For binary markets, we need to look at the market prices
                        # which are usually in a separate field
                        pass

            # Method 2: Check for outcomePrices field (common in Gamma API)
            outcome_prices = market.get('outcomePrices', [])
            if outcome_prices and isinstance(outcome_prices, list):
                if len(outcome_prices) >= 2:
                    # Usually [YES price, NO price]
                    yes_price = float(outcome_prices[0]) * 100
                    no_price = float(outcome_prices[1]) * 100
                elif len(outcome_prices) == 1:
                    # Single outcome
                    yes_price = float(outcome_prices[0]) * 100
                    no_price = 100.0 - yes_price

            # Method 3: Check for lastTradePrice field
            if yes_price == 0.0 and 'lastTradePrice' in market:
                yes_price = float(market.get('lastTradePrice', 0)) * 100
                no_price = 100.0 - yes_price

            # Method 4: Check tokens array
            if yes_price == 0.0 and tokens and isinstance(tokens, list):
                for i, token in enumerate(tokens):
                    if isinstance(token, dict):
                        price = float(token.get('price', token.get('lastPrice', 0)))
                        outcome_name = str(token.get('outcome', '')).upper()

                        if 'YES' in outcome_name or i == 0:
                            yes_price = price * 100
                        elif 'NO' in outcome_name or i == 1:
                            no_price = price * 100

            # Ensure prices are complementary if one is missing
            if yes_price > 0 and no_price == 0:
                no_price = 100.0 - yes_price
            elif no_price > 0 and yes_price == 0:
                yes_price = 100.0 - no_price

            # Volume - Gamma API uses various fields
            volume_24h = float(
                market.get('volume24hr') or
                market.get('volume_24hr') or
                market.get('volume') or
                market.get('volumeNum', 0) or
                0
            )

            # End date - Gamma API structure
            end_date = (
                market.get('endDateIso') or
                market.get('end_date_iso') or
                market.get('endDate') or
                market.get('end_date') or
                market.get('endDateISO') or
                'N/A'
            )

            # Extract just the date portion if it's a full ISO timestamp
            if end_date != 'N/A' and 'T' in str(end_date):
                end_date = str(end_date).split('T')[0]

            # Slug/ID
            slug = (
                market.get('slug') or
                market.get('conditionId') or
                market.get('questionID') or
                ''
            )

            # Active status
            active = market.get('active', True)
            if 'closed' in market:
                active = not market.get('closed', False)

            return {
                'title': title,
                'yes_price': yes_price,
                'no_price': no_price,
                'volume_24h': volume_24h,
                'end_date': end_date,
                'slug': slug,
                'active': active
            }

        except Exception as e:
            logger.error(f"Error parsing market data: {e}")
            logger.exception(e)
            return self._get_empty_market()

    def _get_empty_market(self) -> Dict[str, Any]:
        """Return empty market data structure."""
        return {
            'title': 'Parse Error',
            'yes_price': 0.0,
            'no_price': 0.0,
            'volume_24h': 0.0,
            'end_date': 'N/A',
            'slug': '',
            'active': False
        }

    def close(self):
        """Close the HTTP client."""
        self.client.close()
