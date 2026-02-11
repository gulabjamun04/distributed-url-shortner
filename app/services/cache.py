import redis
import os
import json

# Redis client
# Assuming Redis is running on localhost:6379, as configured in docker-compose.yml
# REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
# REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# For local development with docker-compose, the service name is 'redis'
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


# 24 hours TTL for valid URLs
CACHE_TTL_SECONDS = 24 * 60 * 60
# 5 minutes TTL for null cache entries (cache null pattern)
CACHE_NULL_TTL_SECONDS = 5 * 60

# Use decode_responses=True to get strings instead of bytes
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

async def get_url(short_code: str) -> str | None:
    """
    Checks Redis for the long URL corresponding to the short code.
    Returns the long URL if found, None if not found (including cache null entries).
    """
    cached_data = redis_client.get(short_code)
    if cached_data:
        # Check for cache null pattern
        if cached_data == "NX":  # "NX" stands for "Not Exists"
            return None
        return cached_data
    return None

async def set_url(short_code: str, long_url: str):
    """
    Writes the short_code and long_url to Redis with a 24-hour TTL.
    """
    redis_client.setex(short_code, CACHE_TTL_SECONDS, long_url)

async def set_null_url(short_code: str):
    """
    Implements the 'Cache Null' pattern by setting a placeholder in Redis
    for a short_code that does not exist in the database, with a 5-minute TTL.
    This prevents cache penetration for non-existent URLs.
    """
    redis_client.setex(short_code, CACHE_NULL_TTL_SECONDS, "NX")
