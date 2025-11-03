"""
Polymarket API client for fetching market data using Data API and Gamma API.
"""

import re
import httpx
from typing import List, Dict, Any, Optional
from core.log import get_logger
from core.cache import Cache

logger = get_logger(__name__)

class PolymarketClient:
    """Client for Polymarket Data API."""

    GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
    DATA_API_POSITIONS_URL = "https://data-api.polymarket.com/positions"

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
        Fetch open positions for a wallet using Data API.

        Args:
            wallet_address: Ethereum wallet address

        Returns:
            List of position data dictionaries with market information
        """
        cache_key = f"wallet_positions_{wallet_address}"

        # Try cache first
        cached = self.cache.get(cache_key, ttl=120)  # 2 min TTL
        if cached is not None:
            logger.info(f"Using cached wallet positions ({len(cached)} positions)")
            return cached

        try:
            logger.info(f"Fetching positions for wallet {wallet_address[:10]}... from Data API")

            # Prepare query parameters
            params = {
                "user": wallet_address,
                "limit": 100,
                "sortBy": "CASHPNL",  # Sort by cash P&L
                "sortDirection": "DESC"
            }

            # Make the request with headers
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; PolymarketTerminal/1.0)"
            }
            response = self.client.get(self.DATA_API_POSITIONS_URL, params=params, headers=headers)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            positions = []

            # Handle different response formats
            if isinstance(data, list):
                positions = data
            elif isinstance(data, dict):
                # Try common keys
                if 'data' in data:
                    positions = data['data']
                elif 'positions' in data:
                    positions = data['positions']
                else:
                    logger.warning(f"Unexpected response format: {list(data.keys())}")
                    positions = []

            logger.info(f"Fetched {len(positions)} positions for wallet {wallet_address[:10]}...")

            # Cache the result
            self.cache.set(cache_key, positions)

            return positions

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching wallet positions: {e.response.status_code} - {e.response.text[:200]}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching wallet positions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching wallet positions: {e}")
            logger.exception(e)
            return []

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

    def parse_market_data(self, market_or_position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse market or position data into standardized format.

        Args:
            market_or_position: Raw market/position data from API

        Returns:
            Parsed market data with keys: title, yes_price, no_price, volume_24h, end_date, position_info
        """
        try:
            # Handle both dict and string responses
            if isinstance(market_or_position, str):
                logger.warning(f"Market data is string, skipping: {market_or_position[:100]}")
                return self._get_empty_market()

            if not isinstance(market_or_position, dict):
                logger.warning(f"Market data is not dict, skipping: {type(market_or_position)}")
                return self._get_empty_market()

            # Check if this is a position (has 'market' nested inside) or a market directly
            if 'market' in market_or_position:
                # This is a position from Data API
                market = market_or_position.get('market', {})
                position_info = {
                    'size': market_or_position.get('size', 0),
                    'initial_value': market_or_position.get('initialValue', 0),
                    'current_value': market_or_position.get('currentValue', 0),
                    'cash_pnl': market_or_position.get('cashPnl', 0),
                    'percent_pnl': market_or_position.get('percentPnl', 0),
                    'outcome': market_or_position.get('outcome', ''),
                    'side': market_or_position.get('side', '')  # YES or NO
                }
            else:
                # This is a direct market object
                market = market_or_position
                position_info = None

            # Extract title/question - Data API includes both formats
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

            result = {
                'title': title,
                'yes_price': yes_price,
                'no_price': no_price,
                'volume_24h': volume_24h,
                'end_date': end_date,
                'slug': slug,
                'active': active
            }

            # Add position info if available
            if position_info:
                result['position'] = position_info

            return result

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

    def extract_keywords_from_market(self, market_title: str) -> List[str]:
        """
        Extract relevant keywords from a market title for news searching.

        Args:
            market_title: The market question/title

        Returns:
            List of keyword strings suitable for news searches
        """
        # Remove common question words and phrases
        stop_words = {
            'will', 'be', 'the', 'a', 'an', 'is', 'are', 'was', 'were',
            'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could',
            'would', 'should', 'may', 'might', 'must', 'shall',
            'by', 'before', 'after', 'on', 'in', 'at', 'to', 'for',
            'of', 'with', 'from', 'as', 'into', 'through', 'during',
            'or', 'and', 'but', 'if', 'than', 'more', 'less', 'this',
            'that', 'these', 'those', 'end', 'year'
        }

        # Extract potential entities and phrases
        keywords = []

        # Remove date ranges and years in specific formats
        title = re.sub(r'\b20\d{2}\b', '', market_title)  # Remove years
        title = re.sub(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b', '', title, flags=re.IGNORECASE)

        # Extract quoted phrases
        quoted = re.findall(r'"([^"]+)"', title)
        keywords.extend(quoted)

        # Extract capitalized phrases (likely proper nouns)
        # Match sequences of capitalized words
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', market_title)
        keywords.extend(proper_nouns)

        # Split into words and filter
        words = re.findall(r'\b[A-Za-z]+\b', title.lower())
        significant_words = [w for w in words if len(w) > 3 and w not in stop_words]

        # Take top significant words
        keywords.extend(significant_words[:5])

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and kw_lower not in stop_words:
                seen.add(kw_lower)
                unique_keywords.append(kw)

        return unique_keywords[:8]  # Return top 8 keywords

    def generate_topics_from_positions(self, positions: List[Dict[str, Any]], config=None) -> List[Dict[str, Any]]:
        """
        Generate topic configuration from user's positions for news aggregation.

        Args:
            positions: List of position dictionaries from get_wallet_positions
            config: Optional Config object to load custom keyword buckets

        Returns:
            List of topic dictionaries with keys: key, title, markets, keywords
        """
        topics = []

        for i, position in enumerate(positions[:10], 1):  # Limit to top 10 positions
            parsed = self.parse_market_data(position)
            title = parsed['title']
            slug = parsed.get('slug', '')

            # Create a short key from the title
            key = re.sub(r'[^a-z0-9]+', '_', title[:50].lower()).strip('_')

            # Check for custom keyword bucket first
            if config and slug:
                custom_keywords = config.get_custom_keyword_bucket(slug)
                if custom_keywords:
                    logger.info(f"Using custom keyword bucket for {title[:30]}")
                    keywords = custom_keywords
                else:
                    # Auto-generate keywords
                    keywords = self.extract_keywords_from_market(title)
            else:
                # Auto-generate keywords
                keywords = self.extract_keywords_from_market(title)

            if not keywords:
                # Use title itself as fallback
                keywords = [title[:30]]

            # Shorten title for display
            display_title = title[:40] + '...' if len(title) > 40 else title

            topic = {
                'key': f"position_{i}_{key}",
                'title': display_title,
                'full_title': title,  # Keep full title for editor
                'slug': slug,  # Keep slug for bucket management
                'markets': [parsed],
                'keywords': keywords[:8]  # Up to 8 keywords for search
            }

            topics.append(topic)

        logger.info(f"Generated {len(topics)} topics from {len(positions)} positions")
        return topics

    def close(self):
        """Close the HTTP client."""
        self.client.close()
