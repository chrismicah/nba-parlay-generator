import redis
import functools
import hashlib
import pickle
from typing import Callable

# Set up Redis client (adjust host/port/db as needed)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def redis_cache(ttl: int = 600):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique cache key based on function name and arguments
            key_data = (func.__module__, func.__qualname__, args, kwargs)
            key_bytes = pickle.dumps(key_data)
            cache_key = hashlib.sha256(key_bytes).hexdigest()
            cached = redis_client.get(cache_key)
            if cached is not None:
                return pickle.loads(cached)
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, pickle.dumps(result))
            return result
        return wrapper
    return decorator 