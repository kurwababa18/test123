"""
Configuration management for Polymarket Terminal.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any

class Config:
    """Manages application configuration from config.yaml."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._data = {}
        self.load()
    
    def load(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._data = yaml.safe_load(f)
    
    def save(self):
        """Save current configuration to YAML file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)
    
    @property
    def wallet_address(self) -> str:
        """Get wallet address to monitor."""
        return self._data.get('wallet_address', '')
    
    @property
    def refresh_seconds(self) -> int:
        """Get refresh interval in seconds."""
        return self._data.get('refresh_seconds', 15)
    
    @refresh_seconds.setter
    def refresh_seconds(self, value: int):
        """Set refresh interval."""
        self._data['refresh_seconds'] = max(5, min(300, value))
        self.save()
    
    @property
    def cache_limit(self) -> int:
        """Get maximum cache entries."""
        return self._data.get('cache_limit', 200)
    
    @property
    def cache_ttl_markets(self) -> int:
        """Get cache TTL for markets in seconds."""
        return self._data.get('cache_ttl_markets', 120)
    
    @property
    def cache_ttl_feeds(self) -> int:
        """Get cache TTL for feeds in seconds."""
        return self._data.get('cache_ttl_feeds', 1800)
    
    @property
    def nitter_urls(self) -> List[str]:
        """Get list of Nitter instance URLs."""
        return self._data.get('nitter', {}).get('base_urls', [
            "https://nitter.net",
            "https://nitter.it",
            "https://nitter.poast.org"
        ])
    
    @property
    def markets(self) -> List[Dict[str, Any]]:
        """Get list of markets configuration."""
        return self._data.get('markets', [])

    def get_market_keywords(self, slug: str) -> List[str]:
        """
        Get keyword buckets for a specific market.

        Args:
            slug: Market slug identifier

        Returns:
            List of keywords for that market
        """
        for market in self.markets:
            if market.get('slug') == slug:
                return market.get('keywords', [])
        return []

    def update_market_keywords(self, slug: str, keywords: List[str]) -> bool:
        """
        Update keyword buckets for a market.

        Args:
            slug: Market slug identifier
            keywords: New list of keywords

        Returns:
            True if updated, False if market not found
        """
        for market in self._data.get('markets', []):
            if market.get('slug') == slug:
                market['keywords'] = keywords
                self.save()
                return True
        return False

    def add_market(self, slug: str, title: str, keywords: List[str]):
        """
        Add a new market with keyword buckets.

        Args:
            slug: Market slug identifier
            title: Market title/question
            keywords: Initial keywords for information aggregation
        """
        markets = self._data.get('markets', [])

        # Don't add duplicates
        if any(m.get('slug') == slug for m in markets):
            return

        markets.append({
            'slug': slug,
            'title': title,
            'keywords': keywords
        })
        self._data['markets'] = markets
        self.save()

    def sync_markets(self, position_data: List[Dict[str, Any]], keyword_extractor=None):
        """
        Sync markets from wallet positions.
        Auto-generates keyword buckets if not already configured.

        Args:
            position_data: List of position dictionaries from API
            keyword_extractor: Function to extract keywords from titles
        """
        existing_slugs = {m.get('slug') for m in self.markets}

        for position in position_data:
            slug = position.get('slug', '')
            title = position.get('question', position.get('title', ''))

            if not slug or not title:
                continue

            # Skip if already configured
            if slug in existing_slugs:
                continue

            # Auto-generate keywords
            keywords = []
            if keyword_extractor and callable(keyword_extractor):
                keywords = keyword_extractor(title)

            self.add_market(slug, title, keywords)
