import asyncio
import sys
import os
import random
import string

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

from app.services.cache import get_url, set_url

async def test_cache_operations():
    test_short_code = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    test_long_url = "http://example.com/test_cache_url"

    print(f"Testing cache operations for short_code: {test_short_code}")

    # Test set_url
    print(f"Setting {test_short_code} -> {test_long_url} in cache...")
    await set_url(test_short_code, test_long_url)
    print("Set operation complete.")

    # Test get_url
    print(f"Getting {test_short_code} from cache...")
    retrieved_long_url = await get_url(test_short_code)
    
    if retrieved_long_url == test_long_url:
        print(f"SUCCESS: Retrieved URL matches: {retrieved_long_url}")
    else:
        print(f"FAILURE: Retrieved URL '{retrieved_long_url}' does not match expected '{test_long_url}'")
    
    # Test for a non-existent key (should return None)
    print(f"Getting a non-existent key from cache...")
    non_existent_key = "nonexist"
    retrieved_non_existent = await get_url(non_existent_key)
    if retrieved_non_existent is None:
        print(f"SUCCESS: Non-existent key '{non_existent_key}' correctly returned None.")
    else:
        print(f"FAILURE: Non-existent key '{non_existent_key}' returned '{retrieved_non_existent}', expected None.")


if __name__ == "__main__":
    asyncio.run(test_cache_operations())
