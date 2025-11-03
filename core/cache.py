"""
Simple caching system with TTL support.
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from core.log import get_logger

logger = get_logger(__name__)

class Cache:
    """Simple file-based cache with TTL."""
    
    def __init__(self, cache_dir: str = "cache", max_entries: int = 200):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_entries = max_entries
        self._memory_cache = {}  # In-memory cache for performance
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a key."""
        safe_key = "".join(c if c.isalnum() or c in '-_' else '_' for c in key)
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
        
        Returns:
            Cached value or None if expired/missing
        """
        # Check memory cache first
        if key in self._memory_cache:
            data, timestamp = self._memory_cache[key]
            if time.time() - timestamp < ttl:
                return data
            else:
                del self._memory_cache[key]
        
        # Check file cache
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            timestamp = cache_data.get('timestamp', 0)
            if time.time() - timestamp < ttl:
                data = cache_data.get('data')
                self._memory_cache[key] = (data, timestamp)
                return data
            else:
                # Expired, remove file
                cache_file.unlink(missing_ok=True)
                return None
        except Exception as e:
            logger.error(f"Error reading cache for {key}: {e}")
            cache_file.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, value: Any):
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        """
        timestamp = time.time()
        
        # Store in memory
        self._memory_cache[key] = (value, timestamp)
        
        # Store in file
        cache_file = self._get_cache_file(key)
        try:
            cache_data = {
                'timestamp': timestamp,
                'data': value
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
            
            # Cleanup old entries if too many
            self._cleanup()
        except Exception as e:
            logger.error(f"Error writing cache for {key}: {e}")
    
    def delete(self, key: str):
        """Delete a cache entry."""
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        cache_file = self._get_cache_file(key)
        cache_file.unlink(missing_ok=True)
    
    def clear(self):
        """Clear all cache entries."""
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink(missing_ok=True)
    
    def _cleanup(self):
        """Remove oldest cache files if over limit."""
        cache_files = list(self.cache_dir.glob("*.json"))
        if len(cache_files) > self.max_entries:
            # Sort by modification time
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            # Remove oldest
            for f in cache_files[:len(cache_files) - self.max_entries]:
                f.unlink(missing_ok=True)
