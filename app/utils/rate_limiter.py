import time
from typing import Optional, Dict, Tuple
from collections import defaultdict, deque
import logging
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import redis
from app.config import settings

logger = logging.getLogger(__name__)

class SlidingWindowRateLimiter:
    """Advanced sliding window rate limiter with Redis backing"""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=getattr(settings, 'redis_db', 1),  # Different DB for rate limiting
                decode_responses=True
            )
            self.redis_client.ping()
            self.use_redis = True
            logger.info("Redis rate limiter initialized")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory rate limiter: {str(e)}")
            self.use_redis = False
            self.in_memory_store = defaultdict(lambda: deque())
    
    def check_rate_limit(self, 
                        identifier: str, 
                        limit: int = 100, 
                        window_seconds: int = 60,
                        endpoint: str = "default") -> Tuple[bool, Dict[str, any]]:
        """
        Check if request should be rate limited
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            endpoint: Endpoint identifier for per-endpoint limits
            
        Returns:
            Tuple of (allowed: bool, limit_info: dict)
        """
        current_time = time.time()
        key = f"rate_limit:{endpoint}:{identifier}"
        
        if self.use_redis:
            return self._check_redis_rate_limit(key, limit, window_seconds, current_time)
        else:
            return self._check_memory_rate_limit(key, limit, window_seconds, current_time)
    
    def _check_redis_rate_limit(self, key: str, limit: int, window_seconds: int, current_time: float) -> Tuple[bool, Dict]:
        """Redis-based sliding window rate limiting"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            window_start = current_time - window_seconds
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window_seconds + 1)
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            allowed = current_count <= limit
            
            if not allowed:
                # Remove the request we just added since it's not allowed
                self.redis_client.zrem(key, str(current_time))
            
            # Calculate reset time
            reset_time = current_time + window_seconds
            
            limit_info = {
                "allowed": allowed,
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset_time": reset_time,
                "window_seconds": window_seconds,
                "current_count": current_count
            }
            
            return allowed, limit_info
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {str(e)}")
            # Fallback to allowing request if Redis fails
            return True, {"allowed": True, "error": "rate_limiter_error"}
    
    def _check_memory_rate_limit(self, key: str, limit: int, window_seconds: int, current_time: float) -> Tuple[bool, Dict]:
        """In-memory sliding window rate limiting"""
        request_times = self.in_memory_store[key]
        
        # Remove expired entries
        window_start = current_time - window_seconds
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check if we're over the limit
        allowed = len(request_times) < limit
        
        if allowed:
            request_times.append(current_time)
        
        limit_info = {
            "allowed": allowed,
            "limit": limit,
            "remaining": max(0, limit - len(request_times)),
            "reset_time": current_time + window_seconds,
            "window_seconds": window_seconds,
            "current_count": len(request_times)
        }
        
        return allowed, limit_info
    
    def get_rate_limit_stats(self, identifier: str, endpoint: str = "default") -> Dict[str, any]:
        """Get current rate limit status for identifier"""
        key = f"rate_limit:{endpoint}:{identifier}"
        current_time = time.time()
        
        if self.use_redis:
            try:
                count = self.redis_client.zcard(key)
                ttl = self.redis_client.ttl(key)
                
                return {
                    "identifier": identifier,
                    "endpoint": endpoint,
                    "current_requests": count,
                    "ttl_seconds": ttl,
                    "using_redis": True
                }
            except Exception as e:
                return {"error": str(e), "using_redis": True}
        else:
            request_times = self.in_memory_store[key]
            return {
                "identifier": identifier,
                "endpoint": endpoint,
                "current_requests": len(request_times),
                "using_redis": False
            }
    
    def clear_rate_limit(self, identifier: str, endpoint: str = "default") -> bool:
        """Clear rate limit for specific identifier (admin function)"""
        key = f"rate_limit:{endpoint}:{identifier}"
        
        if self.use_redis:
            try:
                deleted = self.redis_client.delete(key)
                return deleted > 0
            except Exception as e:
                logger.error(f"Error clearing rate limit: {str(e)}")
                return False
        else:
            if key in self.in_memory_store:
                del self.in_memory_store[key]
                return True
            return False

class RateLimitConfig:
    """Configuration for different rate limit tiers"""
    
    TIERS = {
        "basic": {"requests": 100, "window": 3600},      # 100/hour
        "premium": {"requests": 1000, "window": 3600},   # 1000/hour
        "enterprise": {"requests": 10000, "window": 3600} # 10000/hour
    }
    
    ENDPOINT_LIMITS = {
        "query": {"requests": 50, "window": 60},         # 50 queries/minute
        "datasets": {"requests": 100, "window": 60},     # 100/minute
        "schema": {"requests": 200, "window": 60},       # 200/minute
        "templates": {"requests": 50, "window": 60}      # 50/minute
    }

def create_rate_limit_dependency(endpoint: str = "default"):
    """Create FastAPI dependency for rate limiting"""
    
    def rate_limit_dependency(request, current_user: Dict = None):
        limiter = SlidingWindowRateLimiter()
        
        # Determine identifier (user_id or IP)
        if current_user:
            identifier = current_user.get("user_id", "anonymous")
            user_tier = current_user.get("tier", "basic")
            
            # Get user tier limits
            if user_tier in RateLimitConfig.TIERS:
                tier_limits = RateLimitConfig.TIERS[user_tier]
                global_limit = tier_limits["requests"]
                global_window = tier_limits["window"]
            else:
                global_limit = 100
                global_window = 3600
        else:
            # Use IP for anonymous requests
            identifier = request.client.host
            global_limit = 50  # Lower limit for anonymous
            global_window = 3600
        
        # Check global rate limit
        allowed, global_info = limiter.check_rate_limit(
            identifier, global_limit, global_window, "global"
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": global_limit,
                    "window_seconds": global_window,
                    "reset_time": global_info["reset_time"]
                },
                headers={
                    "X-RateLimit-Limit": str(global_limit),
                    "X-RateLimit-Remaining": str(global_info["remaining"]),
                    "X-RateLimit-Reset": str(int(global_info["reset_time"])),
                    "Retry-After": str(global_window)
                }
            )
        
        # Check endpoint-specific rate limit
        if endpoint in RateLimitConfig.ENDPOINT_LIMITS:
            endpoint_config = RateLimitConfig.ENDPOINT_LIMITS[endpoint]
            allowed, endpoint_info = limiter.check_rate_limit(
                identifier, 
                endpoint_config["requests"], 
                endpoint_config["window"], 
                endpoint
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": f"Rate limit exceeded for {endpoint} endpoint",
                        "limit": endpoint_config["requests"],
                        "window_seconds": endpoint_config["window"],
                        "reset_time": endpoint_info["reset_time"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(endpoint_config["requests"]),
                        "X-RateLimit-Remaining": str(endpoint_info["remaining"]),
                        "X-RateLimit-Reset": str(int(endpoint_info["reset_time"])),
                        "Retry-After": str(endpoint_config["window"])
                    }
                )
        
        return {"rate_limit_info": global_info}
    
    return rate_limit_dependency

# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter()
