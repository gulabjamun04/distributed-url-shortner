import asyncio
import pandas as pd
import random
import string
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import SHARD_ENGINES, get_session, Base
from app.models import URL
from app.utils.hashing import get_shard_for_key
import os

# --- Configuration ---
CSV_FILE = "data/urls.csv"
BENCHMARK_KEYS_FILE = "data/benchmark_keys.txt"
NUM_URLS_TO_SEED = 5000
SHORT_CODE_LENGTH = 6

# --- Helper Functions (reusing from app where applicable) ---


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Generates a random alphanumeric short code."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


async def create_url_entry(long_url: str, short_code: str | None = None) -> str:
    """
    Creates a URL entry in the appropriate shard.
    If short_code is None, a new one will be generated.
    """
    if short_code is None:
        short_code = generate_short_code()

    shard_name = get_shard_for_key(short_code)
    async for session in get_session(shard_name):
        new_url = URL(short_code=short_code, long_url=long_url)
        session.add(new_url)
        await session.commit()
        await session.refresh(new_url)
        return new_url.short_code
    return short_code  # Should not be reached


async def main():
    print(f"Seeding database with {NUM_URLS_TO_SEED} URLs from {CSV_FILE}...")

    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file not found at {CSV_FILE}")
        print("Please ensure 'urls.csv' is in the 'data/' directory.")
        return

    # Load URLs from CSV
    try:
        df = pd.read_csv(CSV_FILE)
        # Assuming the CSV has a column named 'url' or similar
        # Adjust column name if necessary
        if 'url' in df.columns:
            all_urls = df['url'].tolist()
        elif 'URL' in df.columns:  # Common alternative
            all_urls = df['URL'].tolist()
        else:
            print(f"Error: Could not find 'url' or 'URL' column in {CSV_FILE}")
            print(f"Available columns: {df.columns.tolist()}")
            return

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Filter for valid URLs and select 5000
    safe_urls = [url for url in all_urls if isinstance(
        url, str) and url.startswith(('http://', 'https://'))]

    if len(safe_urls) < NUM_URLS_TO_SEED:
        print(
            f"Warning: Found only {len(safe_urls)} valid URLs, less than the requested {NUM_URLS_TO_SEED}.")
        urls_to_seed = safe_urls
    else:
        urls_to_seed = random.sample(safe_urls, NUM_URLS_TO_SEED)

    if not urls_to_seed:
        print("No URLs to seed after filtering. Exiting.")
        return

    # Ensure tables are created (re-run startup logic without dropping)
    # This is a simplified version, ideally handled by alembic migrations
    for shard_name, engine in SHARD_ENGINES.items():
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all) # Not dropping in seed script
            await conn.run_sync(Base.metadata.create_all)
        print(f"Ensured database tables for {shard_name}")

    # Seed URLs and collect short codes
    benchmark_short_codes = []
    for i, long_url in enumerate(urls_to_seed):
        try:
            short_code = await create_url_entry(long_url)
            benchmark_short_codes.append(short_code)
            if (i + 1) % 100 == 0:
                print(f"Seeded {i + 1}/{len(urls_to_seed)} URLs.")
        except Exception as e:
            print(f"Error seeding URL '{long_url}': {e}")

    # Save generated short codes
    os.makedirs(os.path.dirname(BENCHMARK_KEYS_FILE), exist_ok=True)
    with open(BENCHMARK_KEYS_FILE, "w") as f:
        for short_code in benchmark_short_codes:
            f.write(f"{short_code}")

    print(f"Successfully seeded {len(benchmark_short_codes)} URLs.")
    print(f"Generated short codes saved to {BENCHMARK_KEYS_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
