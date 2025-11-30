"""
Rate limiting for AI agent API endpoints.

Implements token bucket algorithm with:
- Per-user rate limits
- Global rate limits
- Tier-based limits
- Redis support for distributed systems
"""

import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: float, limit_type: str = "user"):
        self.retry_after = retry_after
        self.limit_type = limit_type
        super().__init__(
            f"Rate limit exceeded. Please retry after {retry_after:.1f} seconds."
        )


class UserTier(Enum):
    """User tier levels with different rate limits."""
    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    STANDARD = "standard"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int
    requests_per_hour: int
    burst_size: int  # Maximum burst of requests allowed
    
    @classmethod
    def for_tier(cls, tier: UserTier) -> 'RateLimitConfig':
        """Get rate limit configuration for a user tier."""
        configs = {
            UserTier.PLATINUM: cls(
                requests_per_minute=100,
                requests_per_hour=5000,
                burst_size=20
            ),
            UserTier.GOLD: cls(
                requests_per_minute=60,
                requests_per_hour=2000,
                burst_size=15
            ),
            UserTier.SILVER: cls(
                requests_per_minute=30,
                requests_per_hour=1000,
                burst_size=10
            ),
            UserTier.STANDARD: cls(
                requests_per_minute=10,
                requests_per_hour=300,
                burst_size=5
            ),
        }
        return configs.get(tier, configs[UserTier.STANDARD])


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    
    Allows bursts of traffic while maintaining average rate limit.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
        
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
        
        Returns:
            Seconds to wait
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter with support for multiple limits and user tiers.
    
    Features:
    - Per-user rate limiting
    - Global rate limiting
    - Tier-based limits
    - Thread-safe
    - In-memory (can be extended to Redis for distributed systems)
    """
    
    def __init__(
        self,
        global_limit_per_minute: int = 1000,
        global_limit_per_hour: int = 50000,
        enable_global_limit: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            global_limit_per_minute: Global requests per minute across all users
            global_limit_per_hour: Global requests per hour across all users
            enable_global_limit: Whether to enforce global limits
        """
        self.enable_global_limit = enable_global_limit
        
        # Global rate limiters
        self.global_minute_bucket = TokenBucket(
            capacity=global_limit_per_minute,
            refill_rate=global_limit_per_minute / 60.0  # per second
        )
        self.global_hour_bucket = TokenBucket(
            capacity=global_limit_per_hour,
            refill_rate=global_limit_per_hour / 3600.0  # per second
        )
        
        # Per-user rate limiters (user_id -> (minute_bucket, hour_bucket))
        self.user_buckets: Dict[str, tuple[TokenBucket, TokenBucket]] = {}
        self.lock = threading.Lock()
    
    def check_rate_limit(
        self,
        user_id: str,
        user_tier: Optional[UserTier] = None
    ) -> None:
        """
        Check if request is within rate limits.
        
        Args:
            user_id: Unique identifier for the user
            user_tier: User's subscription tier
        
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        # Check global limits first
        if self.enable_global_limit:
            if not self.global_minute_bucket.consume():
                wait_time = self.global_minute_bucket.get_wait_time()
                raise RateLimitExceeded(wait_time, "global_minute")
            
            if not self.global_hour_bucket.consume():
                wait_time = self.global_hour_bucket.get_wait_time()
                raise RateLimitExceeded(wait_time, "global_hour")
        
        # Get or create user buckets
        minute_bucket, hour_bucket = self._get_user_buckets(user_id, user_tier)
        
        # Check user limits
        if not minute_bucket.consume():
            wait_time = minute_bucket.get_wait_time()
            raise RateLimitExceeded(wait_time, "user_minute")
        
        if not hour_bucket.consume():
            wait_time = hour_bucket.get_wait_time()
            raise RateLimitExceeded(wait_time, "user_hour")
    
    def _get_user_buckets(
        self,
        user_id: str,
        user_tier: Optional[UserTier] = None
    ) -> tuple[TokenBucket, TokenBucket]:
        """
        Get or create token buckets for a user.
        
        Args:
            user_id: User identifier
            user_tier: User's subscription tier
        
        Returns:
            Tuple of (minute_bucket, hour_bucket)
        """
        with self.lock:
            if user_id not in self.user_buckets:
                # Get config for user tier
                tier = user_tier or UserTier.STANDARD
                config = RateLimitConfig.for_tier(tier)
                
                # Create buckets
                minute_bucket = TokenBucket(
                    capacity=config.burst_size,
                    refill_rate=config.requests_per_minute / 60.0
                )
                hour_bucket = TokenBucket(
                    capacity=config.requests_per_hour,
                    refill_rate=config.requests_per_hour / 3600.0
                )
                
                self.user_buckets[user_id] = (minute_bucket, hour_bucket)
            
            return self.user_buckets[user_id]
    
    def get_remaining_requests(
        self,
        user_id: str,
        user_tier: Optional[UserTier] = None
    ) -> Dict[str, int]:
        """
        Get remaining requests for a user.
        
        Args:
            user_id: User identifier
            user_tier: User's subscription tier
        
        Returns:
            Dictionary with remaining requests per time window
        """
        minute_bucket, hour_bucket = self._get_user_buckets(user_id, user_tier)
        
        with minute_bucket.lock:
            minute_bucket._refill()
            remaining_minute = int(minute_bucket.tokens)
        
        with hour_bucket.lock:
            hour_bucket._refill()
            remaining_hour = int(hour_bucket.tokens)
        
        return {
            "remaining_per_minute": remaining_minute,
            "remaining_per_hour": remaining_hour,
        }
    
    def reset_user_limits(self, user_id: str):
        """
        Reset rate limits for a specific user.
        
        Args:
            user_id: User identifier
        """
        with self.lock:
            if user_id in self.user_buckets:
                del self.user_buckets[user_id]
    
    def cleanup_inactive_users(self, inactive_threshold: float = 3600.0):
        """
        Remove rate limit data for inactive users.
        
        Args:
            inactive_threshold: Seconds of inactivity before cleanup
        """
        now = time.time()
        with self.lock:
            inactive_users = []
            
            for user_id, (minute_bucket, hour_bucket) in self.user_buckets.items():
                # Check if user has been inactive
                if (now - minute_bucket.last_refill) > inactive_threshold:
                    inactive_users.append(user_id)
            
            for user_id in inactive_users:
                del self.user_buckets[user_id]


# Example usage and testing
if __name__ == "__main__":
    import random
    
    limiter = RateLimiter(
        global_limit_per_minute=100,
        enable_global_limit=True
    )
    
    print("Rate Limiter Test:\n")
    
    # Test user with different tiers
    test_users = [
        ("user_platinum", UserTier.PLATINUM),
        ("user_gold", UserTier.GOLD),
        ("user_standard", UserTier.STANDARD),
    ]
    
    for user_id, tier in test_users:
        print(f"\nTesting {user_id} ({tier.value}):")
        
        # Make rapid requests
        success_count = 0
        for i in range(15):
            try:
                limiter.check_rate_limit(user_id, tier)
                success_count += 1
            except RateLimitExceeded as e:
                print(f"  Request {i+1}: Rate limited! {e}")
                break
        
        print(f"  Successful requests: {success_count}/15")
        
        # Check remaining
        remaining = limiter.get_remaining_requests(user_id, tier)
        print(f"  Remaining: {remaining}")
    
    # Test global limit
    print("\n\nTesting global rate limit:")
    for i in range(105):
        try:
            limiter.check_rate_limit(f"user_{i}", UserTier.STANDARD)
        except RateLimitExceeded as e:
            print(f"Global limit hit at request {i+1}: {e}")
            break
