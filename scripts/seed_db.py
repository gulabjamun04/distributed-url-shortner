import pandas as pd
import asyncio
import random
import string
import sys
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

# Import from app
from app.models import URL, Base
from app.db import SHARD_ENGINES, get_session
from app.utils.hashing import get_shard_for_key

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

async def seed_database():
    """
    Reads URLs from data/urls.csv, generates short codes, determines shards,
    and inserts them into the appropriate PostgreSQL shards.
    """
    print("Starting database seeding...")

    # Create tables on all shards if they don't exist
    for shard_name, engine in SHARD_ENGINES.items():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print(f"Ensured tables exist on {shard_name}")

    try:
        df = pd.read_csv('data/urls.csv')
    except FileNotFoundError:
        print("Error: data/urls.csv not found. Please ensure the file exists.")
        return
    except Exception as e:
        print(f"Error reading data/urls.csv: {e}")
        return

    # Filter for valid URLs and take the first 5000
    valid_urls = df[df['url'].str.startswith(('http://', 'https://'))]['url'].head(5000).tolist()
    if not valid_urls:
        print("No valid URLs found in data/urls.csv to seed.")
        return

    print(f"Found {len(valid_urls)} valid URLs to seed.")

    # Prepare for saving benchmark keys
    benchmark_keys = []
    
    # Store tasks for parallel insertion
    insert_tasks = []
    
    # Keep track of generated short codes to handle duplicates during generation
    generated_short_codes = set()

    chars = string.ascii_letters + string.digits

    async def insert_url_with_retry(long_url: str):
        max_retries = 5
        for _ in range(max_retries):
            short_code = ''.join(random.choice(chars) for _ in range(6))
            if short_code in generated_short_codes:
                continue # Regenerate if already generated in this run

            shard_name = get_shard_for_key(short_code)
            
            async for session in get_session(shard_name):
                # Check for actual database duplicates before inserting
                existing_url = await session.execute(
                    select(URL).filter_by(short_code=short_code)
                )
                if existing_url.scalar_one_or_none():
                    continue # Regenerate if already in DB

                try:
                    new_url = URL(short_code=short_code, long_url=long_url)
                    session.add(new_url)
                    await session.commit()
                    await session.refresh(new_url)
                    generated_short_codes.add(short_code)
                    benchmark_keys.append(short_code)
                    return True
                except Exception as e:
                    # This catch is mainly for unexpected DB errors,
                    # duplicates are handled by the select check above.
                    print(f"Warning: Failed to insert URL {long_url} with short code {short_code} into {shard_name}: {e}. Retrying...")
                    await session.rollback() # Rollback in case of an error
                    continue
        print(f"Error: Failed to insert URL {long_url} after {max_retries} retries.")
        return False

    for i, url in enumerate(valid_urls):
        insert_tasks.append(insert_url_with_retry(url))
        
        if len(insert_tasks) >= 100 or i == len(valid_urls) - 1:
            await asyncio.gather(*insert_tasks)
            insert_tasks = [] # Clear tasks for the next batch
            
        if (i + 1) % 500 == 0:
            print(f"Inserted {i + 1}/{len(valid_urls)} URLs...")

    # Save benchmark keys
    try:
        with open('data/benchmark_keys.txt', 'w') as f:
            for key in benchmark_keys:
                f.write(f"{key}\n")
        print(f"Seeded {len(benchmark_keys)} URLs. Keys saved to data/benchmark_keys.txt")
    except IOError as e:
        print(f"Error saving benchmark keys to data/benchmark_keys.txt: {e}")

    # Cleanly dispose all engine connection pools to avoid asyncpg CancelledError noise
    for engine in SHARD_ENGINES.values():
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(seed_database())
