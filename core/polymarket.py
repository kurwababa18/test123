"""
Polymarket API client for fetching market data.
"""

import httpx
from typing import List, Dict, Any, Optional
from core.log import get_logger
from core.cache import Cache

logger = get_logger(__name__)

class PolymarketClient:
    """Client for Polymarket Gamma API."""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self, cache: Cache):
        self.cache = cache
        self.client = httpx.Client(timeout=10.0)
    
    def get_wallet_positions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Fetch open positions for a wallet.
        
        Args:
            wallet_address: Ethereum wallet address
        
        Returns:
            List of market data dictionaries
        """
        cache_key = f"wallet_positions_{wallet_address}"
        
        # Try cache first
        cached = self.cache.get(cache_key, ttl=120)  # 2 min TTL
        if cached is not None:
            logger.info(f"Using cached wallet positions ({len(cached)} markets)")
            return cached
        
        try:
            url = f"{self.BASE_URL}/markets"
            params = {"wallet": wallet_address}
            
            logger.info(f"Fetching positions for wallet {wallet_address[:10]}...")
            response = self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            markets = []
            
            # Parse response
            if isinstance(data, list):
                markets = data
            elif isinstance(data, dict) and 'data' in data:
                markets = data['data']
            
            logger.info(f"Fetched {len(markets)} markets")
            
            # Cache the result
            self.cache.set(cache_key, markets)
            
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching wallet positions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching wallet positions: {e}")
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
            url = f"{self.BASE_URL}/markets/{slug}"
            
            logger.info(f"Fetching market: {slug}")
            response = self.client.get(url)
            response.raise_for_status()
            
            market = response.json()
            
            # Cache the result
            self.cache.set(cache_key, market)
            
            return market
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching market {slug}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching market {slug}: {e}")
            return None
    
    def parse_market_data(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse market data into standardized format.
        
        Args:
            market: Raw market data from API
        
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
            
            # Extract basic info
            title = market.get('question', market.get('title', 'Unknown Market'))
            
            # Parse outcomes (YES/NO prices)
            outcomes = market.get('outcomes', [])
            yes_price = 0.0
            no_price = 0.0
            
            if isinstance(outcomes, list):
                for outcome in outcomes:
                    if isinstance(outcome, dict):
                        outcome_name = str(outcome.get('outcome', '')).upper()
                        price = float(outcome.get('price', 0))
                        
                        if 'YES' in outcome_name:
                            yes_price = price * 100  # Convert to cents
                        elif 'NO' in outcome_name:
                            no_price = price * 100  # Convert to cents
            
            # Volume and end date
            volume_24h = float(market.get('volume24hr', market.get('volume_24h', 0)))
            end_date = market.get('endDateIso', market.get('end_date_iso', market.get('endDate', 'N/A')))
            
            return {
                'title': title,
                'yes_price': yes_price,
                'no_price': no_price,
                'volume_24h': volume_24h,
                'end_date': end_date,
                'slug': market.get('slug', ''),
                'active': market.get('active', True)
            }
        except Exception as e:
            logger.error(f"Error parsing market data: {e}")
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
