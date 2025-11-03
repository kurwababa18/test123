"""
Spike detection for keyword/tweet volume.
"""

import time
from typing import Dict, List, Any
from core.cache import Cache
from core.log import get_logger

logger = get_logger(__name__)

class SpikeDetector:
    """Detects spikes in keyword mentions/volume."""

    def __init__(self, cache: Cache):
        self.cache = cache

    def calculate_spike(self, keyword: str, current_count: int) -> Dict[str, Any]:
        """
        Calculate if there's a spike for a keyword.

        Args:
            keyword: The keyword being tracked
            current_count: Current mention count

        Returns:
            Dict with spike_percent, is_spike, historical_avg
        """
        cache_key = f"keyword_history_{keyword}"

        # Get historical data
        history = self.cache.get(cache_key, ttl=86400) or []  # 24 hour history

        # Add current count with timestamp
        timestamp = int(time.time())
        history.append({
            'count': current_count,
            'timestamp': timestamp
        })

        # Keep last 24 hours only
        cutoff = timestamp - 86400
        history = [h for h in history if h['timestamp'] > cutoff]

        # Calculate average
        if len(history) < 2:
            # Not enough data
            self.cache.set(cache_key, history)
            return {
                'spike_percent': 0,
                'is_spike': False,
                'historical_avg': current_count,
                'confidence': 'low'
            }

        # Calculate historical average (excluding current)
        historical_counts = [h['count'] for h in history[:-1]]
        avg = sum(historical_counts) / len(historical_counts) if historical_counts else 1

        # Calculate spike percentage
        if avg == 0:
            spike_pct = 0 if current_count == 0 else 100
        else:
            spike_pct = ((current_count - avg) / avg) * 100

        # Determine if it's a spike (>50% increase)
        is_spike = spike_pct > 50

        # Save updated history
        self.cache.set(cache_key, history)

        return {
            'spike_percent': spike_pct,
            'is_spike': is_spike,
            'historical_avg': avg,
            'current_count': current_count,
            'confidence': 'high' if len(history) > 10 else 'medium'
        }

    def analyze_keywords(self, keywords: List[str], keyword_counts: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple keywords for spikes.

        Args:
            keywords: List of keywords to track
            keyword_counts: Dict mapping keyword to current count

        Returns:
            Dict mapping keyword to spike analysis
        """
        results = {}

        for keyword in keywords:
            count = keyword_counts.get(keyword, 0)
            analysis = self.calculate_spike(keyword, count)
            results[keyword] = analysis

            if analysis['is_spike']:
                logger.info(f"🔥 SPIKE DETECTED: '{keyword}' +{analysis['spike_percent']:.0f}% ({count} mentions)")

        return results
