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
    def polymarket_api_key(self) -> str:
        """Get Polymarket API key."""
        return self._data.get('polymarket_api_key') or None

    @property
    def polymarket_api_secret(self) -> str:
        """Get Polymarket API secret."""
        return self._data.get('polymarket_api_secret') or None

    @property
    def polymarket_api_passphrase(self) -> str:
        """Get Polymarket API passphrase."""
        return self._data.get('polymarket_api_passphrase') or None

    @property
    def nitter_urls(self) -> List[str]:
        """Get list of Nitter instance URLs."""
        return self._data.get('nitter', {}).get('base_urls', [
            "https://nitter.net",
            "https://nitter.it",
            "https://nitter.poast.org"
        ])
    
    @property
    def topics(self) -> List[Dict[str, Any]]:
        """Get list of topics/tabs configuration."""
        return self._data.get('topics', [])
    
    def update_topic_title(self, key: str, new_title: str):
        """Update a topic's display title."""
        for topic in self._data.get('topics', []):
            if topic.get('key') == key:
                topic['title'] = new_title
                self.save()
                return True
        return False
    
    def delete_topic(self, key: str) -> bool:
        """Delete a topic by key."""
        topics = self._data.get('topics', [])
        original_len = len(topics)
        self._data['topics'] = [t for t in topics if t.get('key') != key]
        if len(self._data['topics']) < original_len:
            self.save()
            return True
        return False
    
    def add_topic(self, key: str, title: str, keywords: List[str]):
        """Add a new topic."""
        topics = self._data.get('topics', [])
        topics.append({
            'key': key,
            'title': title,
            'markets': [],
            'keywords': keywords
        })
        self._data['topics'] = topics
        self.save()
