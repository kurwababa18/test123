"""
News and social media feed sources (Twitter/Nitter, Google News, RSS).
"""

import httpx
import feedparser
import time
from typing import List, Dict, Any
from urllib.parse import quote_plus
from core.log import get_logger
from core.cache import Cache

logger = get_logger(__name__)

class FeedSource:
    """Aggregates feeds from multiple sources."""
    
    def __init__(self, cache: Cache, nitter_urls: List[str]):
        self.cache = cache
        self.nitter_urls = nitter_urls
        self.current_nitter_idx = 0
        self.client = httpx.Client(timeout=15.0, follow_redirects=True)
        self.rate_limit_until = {}  # Track rate limits per source
    
    def _get_nitter_url(self) -> str:
        """Get current Nitter URL with rotation."""
        if not self.nitter_urls:
            return "https://nitter.net"
        
        url = self.nitter_urls[self.current_nitter_idx]
        return url
    
    def _rotate_nitter(self):
        """Rotate to next Nitter instance."""
        if len(self.nitter_urls) > 1:
            self.current_nitter_idx = (self.current_nitter_idx + 1) % len(self.nitter_urls)
            logger.info(f"Rotated to Nitter: {self._get_nitter_url()}")
    
    def _is_rate_limited(self, source: str) -> bool:
        """Check if a source is currently rate limited."""
        if source in self.rate_limit_until:
            if time.time() < self.rate_limit_until[source]:
                return True
            else:
                del self.rate_limit_until[source]
        return False
    
    def _set_rate_limit(self, source: str, duration: int = 300):
        """Set rate limit for a source (default 5 minutes)."""
        self.rate_limit_until[source] = time.time() + duration
        logger.warning(f"Rate limited {source} for {duration}s")
    
    def fetch_nitter_search(self, query: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch tweets from Nitter search RSS.
        
        Args:
            query: Search query
            max_pages: Number of RSS pages to fetch (for backfill)
        
        Returns:
            List of tweet dictionaries
        """
        cache_key = f"nitter_search_{query}"
        
        # Check cache
        cached = self.cache.get(cache_key, ttl=1800)  # 30 min
        if cached is not None:
            return cached
        
        # Check rate limit
        if self._is_rate_limited('nitter'):
            logger.warning("Nitter rate limited, using cache")
            return []
        
        tweets = []
        attempts = 0
        max_attempts = len(self.nitter_urls)
        
        while attempts < max_attempts:
            try:
                nitter_url = self._get_nitter_url()
                search_url = f"{nitter_url}/search/rss"
                params = {"q": query}
                
                logger.info(f"Fetching Nitter search: {query[:50]}...")
                response = self.client.get(search_url, params=params)
                
                if response.status_code == 429:
                    self._set_rate_limit('nitter')
                    self._rotate_nitter()
                    attempts += 1
                    continue
                
                response.raise_for_status()
                
                # Parse RSS feed
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:10]:  # Limit to 10 per query
                    tweets.append({
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'source': 'Twitter/X'
                    })
                
                logger.info(f"Fetched {len(tweets)} tweets for query")
                break
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching Nitter: {e}")
                self._rotate_nitter()
                attempts += 1
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error fetching Nitter: {e}")
                self._rotate_nitter()
                attempts += 1
        
        # Cache results
        if tweets:
            self.cache.set(cache_key, tweets)
        
        return tweets
    
    def fetch_google_news(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch news from Google News RSS.
        
        Args:
            query: Search query
        
        Returns:
            List of news article dictionaries
        """
        cache_key = f"google_news_{query}"
        
        # Check cache
        cached = self.cache.get(cache_key, ttl=1800)  # 30 min
        if cached is not None:
            return cached
        
        # Check rate limit
        if self._is_rate_limited('google_news'):
            return []
        
        articles = []
        
        try:
            base_url = "https://news.google.com/rss/search"
            params = {
                "q": query,
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en"
            }
            
            logger.info(f"Fetching Google News: {query[:50]}...")
            response = self.client.get(base_url, params=params)
            
            if response.status_code == 429:
                self._set_rate_limit('google_news')
                return []
            
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries[:5]:  # Limit to 5
                articles.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': 'Google News'
                })
            
            logger.info(f"Fetched {len(articles)} news articles")
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Google News: {e}")
        except Exception as e:
            logger.error(f"Error fetching Google News: {e}")
        
        # Cache results
        if articles:
            self.cache.set(cache_key, articles)
        
        return articles
    
    def fetch_rss_feed(self, url: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Fetch a generic RSS feed.
        
        Args:
            url: RSS feed URL
            source_name: Display name for the source
        
        Returns:
            List of feed item dictionaries
        """
        cache_key = f"rss_{url}"
        
        # Check cache
        cached = self.cache.get(cache_key, ttl=1800)  # 30 min
        if cached is not None:
            return cached
        
        # Check rate limit
        if self._is_rate_limited(f"rss_{url}"):
            return []
        
        items = []
        
        try:
            logger.info(f"Fetching RSS: {source_name}")
            response = self.client.get(url)
            
            if response.status_code == 429:
                self._set_rate_limit(f"rss_{url}")
                return []
            
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries[:5]:  # Limit to 5
                items.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': source_name
                })
            
            logger.info(f"Fetched {len(items)} items from {source_name}")
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {source_name}: {e}")
        except Exception as e:
            logger.error(f"Error fetching {source_name}: {e}")
        
        # Cache results
        if items:
            self.cache.set(cache_key, items)
        
        return items
    
    def aggregate_feeds(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Aggregate feeds from all sources for given keywords.
        
        Args:
            keywords: List of search keywords
        
        Returns:
            Combined and deduplicated list of feed items
        """
        all_items = []
        seen_titles = set()
        
        # Fetch from each keyword
        for keyword in keywords[:5]:  # Limit to 5 keywords to avoid rate limits
            # Twitter/Nitter
            tweets = self.fetch_nitter_search(keyword)
            all_items.extend(tweets)
            
            # Google News
            news = self.fetch_google_news(keyword)
            all_items.extend(news)
        
        # Deduplicate by title
        unique_items = []
        for item in all_items:
            title_lower = item['title'].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_items.append(item)
        
        # Sort by published date (newest first)
        unique_items.sort(key=lambda x: x.get('published', ''), reverse=True)
        
        return unique_items[:20]  # Return top 20
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
