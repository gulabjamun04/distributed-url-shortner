import asyncio
import pandas as pd
import random
import string
import sys
import os

# Set RUNNING_LOCALLY before importing app modules
os.environ["RUNNING_LOCALLY"] = "true"

# Set PYTHONPATH to include project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import URL
from app.db import SHARD_ENGINES, get_session, Base
from app.utils.hashing import get_shard_for_key
from sqlalchemy.future import select


# Configuration
CSV_FILE = "data/urls.csv"
BENCHMARK_KEYS_FILE = "data/benchmark_keys.txt"
NUM_URLS_TO_SEED = 5000
SHORT_CODE_LENGTH = 6
BATCH_SIZE = 30 # Concurrency limit

async def create_url_entry(long_url):
    """Creates a URL entry, handling duplicates."""
    while True:
        short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=SHORT_CODE_LENGTH))
        shard_name = get_shard_for_key(short_code)
        
        async for session in get_session(shard_name):
            try:
                result = await session.execute(select(URL).filter(URL.short_code == short_code))
                if result.scalar_one_or_none() is None:
                    new_url = URL(short_code=short_code, long_url=long_url)
                    session.add(new_url)
                    await session.commit()
                    return short_code
            except Exception as e:
                print(f"Error inserting {long_url}: {e}")
                return None # Indicate failure
        # If we are here, it means there was a collision, so we loop and try again.

async def seed_database():
    """Seeds the database with URLs from a CSV file."""
    print("--- Starting Database Seeding ---")

    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"Error: {CSV_FILE} not found.")
        return

    valid_urls_df = df[df['url'].str.startswith(('http://', 'https://'), na=False)]
    urls_to_seed = valid_urls_df['url'].head(NUM_URLS_TO_SEED).tolist()
    
    print(f"Found {len(urls_to_seed)} URLs to seed.")

    for engine in SHARD_ENGINES.values():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    print("Database tables ensured.")

    all_short_codes = []
    
    last_progress_report = 0
    for i in range(0, len(urls_to_seed), BATCH_SIZE):
        batch_urls = urls_to_seed[i:i+BATCH_SIZE]
        
        tasks = [create_url_entry(url) for url in batch_urls]
        results = await asyncio.gather(*tasks)
        
        successful_codes = [code for code in results if code]
        all_short_codes.extend(successful_codes)
        
        if len(all_short_codes) - last_progress_report >= 500:
             print(f"Inserted {len(all_short_codes)}/{len(urls_to_seed)} URLs...")
             last_progress_report = len(all_short_codes)

    with open(BENCHMARK_KEYS_FILE, "w") as f:
        for code in all_short_codes:
            if code:
                f.write(f"{code}\n")

    print(f"\n--- Seeding Complete ---")
    print(f"Seeded {len(all_short_codes)} URLs. Keys saved to {BENCHMARK_KEYS_FILE}")


if __name__ == "__main__":
    asyncio.run(seed_database())
