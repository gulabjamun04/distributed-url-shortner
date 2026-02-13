import asyncio
import aiohttp
import time
import pandas as pd
import uvloop
import os
import random


async def fetch(session, url):
    start_time = time.monotonic()
    try:
        async with session.get(url) as response:
            await response.text()
            return response.status
    except aiohttp.ClientError as e:
        return f"Error: {e}"
    finally:
        end_time = time.monotonic()
        # You can process or store latency here if needed
        # print(f"Request to {url} took {end_time - start_time:.4f} seconds")


async def generate_load(target_rps: int, duration: int, base_url: str, urls_to_hit: list):
    successful_requests = 0
    failed_requests = 0
    total_requests = 0
    start_time = time.monotonic()

    async with aiohttp.ClientSession() as session:
        while True:
            elapsed_time = time.monotonic() - start_time
            if elapsed_time >= duration:
                break

            tasks = []
            requests_this_second = 0
            second_start_time = time.monotonic()

            while requests_this_second < target_rps:
                short_code = random.choice(urls_to_hit)
                url = f"{base_url}/{short_code}"
                tasks.append(fetch(session, url))
                requests_this_second += 1

                if len(tasks) >= target_rps:  # Avoid creating too many tasks at once
                    break

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    total_requests += 1
                    if isinstance(result, int) and 200 <= result < 400:
                        successful_requests += 1
                    else:
                        failed_requests += 1

            # Adjust sleep time to meet target RPS
            current_second_duration = time.monotonic() - second_start_time
            sleep_time = (1.0 / target_rps * requests_this_second) - \
                current_second_duration
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    end_time = time.monotonic()
    print(f"Load Test Results:")
    print(f"Total duration: {end_time - start_time:.2f} seconds")
    print(f"Total requests: {total_requests}")
    print(f"Successful requests: {successful_requests}")
    print(f"Failed requests: {failed_requests}")
    print(f"Achieved RPS: {total_requests / (end_time - start_time):.2f}")


async def main():
    # Set uvloop as the event loop policy for performance
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    target_rps = 1000  # Desired requests per second
    duration = 60    # Duration of the test in seconds

    # --- IMPORTANT: CHOOSE YOUR BASE_URL ---
    # Public Cloudflare Tunnel URL (replace with your actual URL)
    # base_url = "https://api.distributed-url-shortner.online"
    # Or local URL if you want to test against your local Docker setup
    base_url = "http://localhost:8000"

    # Load benchmark keys
    try:
        # Assuming data/benchmark_keys.txt contains one short_code per line
        # and the file was created by scripts/seed_db.py
        with open("data/benchmark_keys.txt", "r") as f:
            urls_to_hit = [line.strip() for line in f if line.strip()]
        if not urls_to_hit:
            print(
                "Error: data/benchmark_keys.txt is empty. Please run scripts/seed_db.py first.")
            return
    except FileNotFoundError:
        print(
            "Error: data/benchmark_keys.txt not found. Please run scripts/seed_db.py first.")
        return

    print(
        f"Starting load test to {base_url} at {target_rps} RPS for {duration} seconds...")
    await generate_load(target_rps, duration, base_url, urls_to_hit)

if __name__ == "__main__":
    asyncio.run(main())
