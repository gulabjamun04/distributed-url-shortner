import asyncio
import aiohttp
import time
import json
import uvloop
import random
import argparse
from collections import deque
from datetime import datetime, timezone


async def fetch(session, url, latencies):
    start_time = time.monotonic()
    try:
        async with session.get(url, allow_redirects=False) as response:
            await response.read()
            latency = (time.monotonic() - start_time) * 1000
            latencies.append(latency)
            return response.status
    except aiohttp.ClientError:
        return -1


async def generate_load(target_rps: int, duration: int, base_url: str, urls_to_hit: list):
    successful_requests = 0
    failed_requests = 0
    total_requests = 0
    latencies = deque(maxlen=50000)
    start_time = time.monotonic()

    # ANSI colors
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        last_print = 0
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= duration:
                break

            # Fire a batch of requests for this tick
            batch_size = target_rps
            tasks = []
            for _ in range(batch_size):
                short_code = random.choice(urls_to_hit)
                url = f"{base_url}/{short_code}"
                tasks.append(fetch(session, url, latencies))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                total_requests += 1
                if isinstance(result, int) and 200 <= result < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1

            # Live stats every second
            now = time.monotonic()
            if int(now - start_time) > last_print:
                last_print = int(now - start_time)
                rps = total_requests / (now - start_time)
                color = GREEN if rps >= 1000 else YELLOW if rps >= 500 else RED
                recent = list(latencies)[-1000:]
                avg_lat = sum(recent) / len(recent) if recent else 0
                err_rate = (failed_requests / total_requests * 100) if total_requests else 0
                print(
                    f"[{int(now - start_time):>3}s] Total: {total_requests:<7} | "
                    f"{color}RPS: {rps:<8.2f}{RESET} | "
                    f"Avg Latency: {avg_lat:<7.2f}ms | "
                    f"Errors: {err_rate:.2f}%"
                )

            # Pace to ~1 batch per second
            batch_elapsed = time.monotonic() - (start_time + elapsed)
            sleep_time = 1.0 - batch_elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    end_time = time.monotonic()
    total_time = end_time - start_time

    # Calculate percentiles
    sorted_lat = sorted(latencies)
    p50 = sorted_lat[int(len(sorted_lat) * 0.50)] if sorted_lat else 0
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)] if sorted_lat else 0

    print(f"\n--- Test Summary ---")
    print(f"Total test duration: {total_time:.2f}s")
    print(f"Total requests:      {total_requests}")
    print(f"Successful requests: {successful_requests}")
    print(f"Errored requests:    {failed_requests}")
    print(f"Requests per second: {total_requests / total_time:.2f}")
    print(f"\n--- Latency Percentiles ---")
    print(f"p50 (Median): {p50:.2f}ms")
    print(f"p95:          {p95:.2f}ms")
    print(f"p99:          {p99:.2f}ms")
    print(f"--------------------")

    # Save results JSON
    results = {
        "test_config": {
            "url": base_url,
            "target_rps": target_rps,
            "duration": duration,
        },
        "summary": {
            "total_duration_s": round(total_time, 2),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "errored_requests": failed_requests,
            "requests_per_second": round(total_requests / total_time, 2),
        },
        "latency_percentiles_ms": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    with open("tests/load_test_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to tests/load_test_results.json")

    return results


async def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    parser = argparse.ArgumentParser(description="Async load testing tool.")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="Target URL.")
    parser.add_argument("--rps", type=int, default=1500, help="Target requests per second.")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds.")
    args = parser.parse_args()

    try:
        with open("data/benchmark_keys.txt", "r") as f:
            urls_to_hit = [line.strip() for line in f if line.strip()]
        if not urls_to_hit:
            print("Error: data/benchmark_keys.txt is empty.")
            return
    except FileNotFoundError:
        print("Error: data/benchmark_keys.txt not found. Run scripts/seed_db.py first.")
        return

    print(f"Starting async load test to {args.url} at {args.rps} target RPS for {args.duration}s...")
    await generate_load(args.rps, args.duration, args.url, urls_to_hit)

if __name__ == "__main__":
    asyncio.run(main())
