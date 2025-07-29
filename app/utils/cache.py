import redis
import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class QueryCache:
    """Advanced query result caching system"""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=getattr(settings, 'redis_db', 0),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis cache disabled: {str(e)}")
            self.enabled = False
    
    def _generate_cache_key(self, query: str, params: Optional[Dict] = None, user_id: str = None) -> str:
        """Generate unique cache key for query"""
        # Normalize query (remove extra whitespace, convert to lowercase)
        normalized_query = ' '.join(query.strip().lower().split())
        
        # Include parameters and user context in key
        key_data = {
            'query': normalized_query,
            'params': params or {},
            'user_id': user_id
        }
        
        # Create hash of the key data
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"query_cache:{key_hash}"
    
    def get(self, query: str, params: Optional[Dict] = None, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get cached query result"""
        if not self.enabled:
            return None
        
        try:
            cache_key = self._generate_cache_key(query, params, user_id)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = json.loads(cached_data)
                logger.info(f"Cache hit for query: {query[:50]}...")
                
                # Update hit statistics
                self._update_cache_stats(cache_key, hit=True)
                return result
            
            logger.debug(f"Cache miss for query: {query[:50]}...")
            self._update_cache_stats(cache_key, hit=False)
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(self, query: str, result: Dict[str, Any], params: Optional[Dict] = None, 
            user_id: str = None, ttl: int = 3600) -> bool:
        """Cache query result with TTL"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_cache_key(query, params, user_id)
            
            # Add metadata to cached result
            cached_data = {
                'result': result,
                'cached_at': str(datetime.utcnow()),
                'query_hash': cache_key,
                'ttl': ttl
            }
            
            success = self.redis_client.setex(
                cache_key,
                timedelta(seconds=ttl),
                json.dumps(cached_data, default=str)
            )
            
            if success:
                logger.info(f"Cached query result: {query[:50]}... (TTL: {ttl}s)")
                
                # Track cache usage
                self._track_cache_usage(cache_key, len(json.dumps(result)))
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(f"query_cache:*{pattern}*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")
            return 0
    
    def clear_user_cache(self, user_id: str) -> int:
        """Clear all cached queries for a specific user"""
        return self.invalidate_pattern(f'"user_id":"{user_id}"')
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            info = self.redis_client.info()
            stats_key = "cache_stats"
            stats = self.redis_client.hgetall(stats_key) or {}
            
            return {
                "enabled": True,
                "redis_memory_used": info.get('used_memory_human', 'N/A'),
                "redis_connected_clients": info.get('connected_clients', 0),
                "cache_hits": int(stats.get('hits', 0)),
                "cache_misses": int(stats.get('misses', 0)),
                "hit_rate": self._calculate_hit_rate(stats),
                "total_queries": int(stats.get('total_queries', 0)),
                "cache_size_bytes": int(stats.get('size_bytes', 0))
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"enabled": True, "error": str(e)}
    
    def _update_cache_stats(self, cache_key: str, hit: bool):
        """Update cache hit/miss statistics"""
        try:
            stats_key = "cache_stats"
            if hit:
                self.redis_client.hincrby(stats_key, 'hits', 1)
            else:
                self.redis_client.hincrby(stats_key, 'misses', 1)
        except Exception as e:
            logger.error(f"Error updating cache stats: {str(e)}")
    
    def _track_cache_usage(self, cache_key: str, size_bytes: int):
        """Track cache usage metrics"""
        try:
            stats_key = "cache_stats"
            self.redis_client.hincrby(stats_key, 'total_queries', 1)
            self.redis_client.hincrby(stats_key, 'size_bytes', size_bytes)
        except Exception as e:
            logger.error(f"Error tracking cache usage: {str(e)}")
    
    def _calculate_hit_rate(self, stats: Dict) -> float:
        """Calculate cache hit rate percentage"""
        hits = int(stats.get('hits', 0))
        misses = int(stats.get('misses', 0))
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)

# Global cache instance
query_cache = QueryCache()
