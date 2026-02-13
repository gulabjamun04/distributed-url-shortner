import requests
import threading
import time
import random
import argparse
import json
from collections import defaultdict, deque
from datetime import datetime

# --- Globals ---
stats = {
    'total': 0,
    'success': 0,
    'errors': 0,
    'latencies': deque(maxlen=10000)
}
stats_lock = threading.Lock()
stop_flag = threading.Event()

# --- ASCII Banner ---
BANNER = """
███████╗████████╗██████╗ ███████╗███████╗███████╗
██╔════╝╚══██╔══╝██╔══██╗██╔════╝██╔════╝██╔════╝
███████╗   ██║   ██████╔╝███████╗███████╗███████╗
╚════██║   ██║   ██╔══██╗╚════██║╚════██║╚════██║
███████║   ██║   ██║  ██║███████║███████║███████║
╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
A simple but effective load testing tool.
"""

def worker(worker_id, keys, target_url):
    """Sends requests to the target URL with random keys."""
    while not stop_flag.is_set():
        key = random.choice(keys)
        url = f'{target_url}/{key}'
        start_time = time.time()
        try:
            response = requests.get(url, timeout=5, allow_redirects=False)
            latency = (time.time() - start_time) * 1000  # in ms

            with stats_lock:
                stats['total'] += 1
                if 300 <= response.status_code < 400:
                    stats['success'] += 1
                    stats['latencies'].append(latency)
                else:
                    stats['errors'] += 1

        except requests.RequestException:
            with stats_lock:
                stats['total'] += 1
                stats['errors'] += 1
        
        time.sleep(0.001)

def monitor_stats(start_time):
    """Monitors and prints stats every second."""
    # ANSI color codes
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

    while not stop_flag.is_set():
        time.sleep(1)
        with stats_lock:
            total_requests = stats['total']
            latencies = list(stats['latencies']) # Create a copy

        elapsed_time = time.time() - start_time
        if elapsed_time == 0:
            continue

        rps = total_requests / elapsed_time

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
        else:
            avg_latency = 0
        
        error_rate = (stats['errors'] / total_requests * 100) if total_requests > 0 else 0

        # Color coding for RPS
        if rps >= 1000:
            color = GREEN
        elif 500 <= rps < 1000:
            color = YELLOW
        else:
            color = RED
        
        print(
            f"[{int(elapsed_time):>3}s] Total: {total_requests:<7} | "
            f"{color}RPS: {rps:<8.2f}{RESET} | "
            f"Avg Latency: {avg_latency:<5.2f}ms | "
            f"Errors: {error_rate:.2f}%"
        )

def calculate_percentiles(latencies_list):
    """Calculates p50, p95, p99 latencies."""
    if not latencies_list:
        return 0, 0, 0
    
    sorted_latencies = sorted(latencies_list)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
    return p50, p95, p99

def main():
    """Main function to run the load test."""
    print(BANNER)
    parser = argparse.ArgumentParser(description="A simple load testing tool.")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="Target URL for the load test.")
    parser.add_argument("--workers", type=int, default=300, help="Number of concurrent workers.")
    parser.add_argument("--duration", type=int, default=30, help="Duration of the test in seconds.")
    args = parser.parse_args()

    try:
        with open("data/benchmark_keys.txt", "r") as f:
            keys = [line.strip() for line in f if line.strip()]
        if not keys:
            print("Error: data/benchmark_keys.txt is empty.")
            return
    except FileNotFoundError:
        print("Error: data/benchmark_keys.txt not found.")
        return

    print("--- Test Configuration ---")
    print(f"URL:      {args.url}")
    print(f"Workers:  {args.workers}")
    print(f"Duration: {args.duration}s")
    print("--------------------------\n")

    threads = []
    start_time = time.time()

    # Start worker threads
    for i in range(args.workers):
        thread = threading.Thread(target=worker, args=(i, keys, args.url))
        threads.append(thread)
        thread.start()

    # Start monitor thread
    monitor_thread = threading.Thread(target=monitor_stats, args=(start_time,))
    monitor_thread.start()

    try:
        # Let the test run for the specified duration
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Stopping test...")
    finally:
        # Signal all threads to stop
        stop_flag.set()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()
        monitor_thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # --- Final Statistics ---
        final_latencies = list(stats['latencies'])
        p50, p95, p99 = calculate_percentiles(final_latencies)

        print("\n--- Test Summary ---")
        print(f"Total test duration: {total_time:.2f}s")
        print(f"Total requests:      {stats['total']}")
        print(f"Successful requests: {stats['success']}")
        print(f"Errored requests:    {stats['errors']}")
        print(f"Requests per second: {stats['total'] / total_time:.2f}")

        print("\n--- Latency Percentiles ---")
        print(f"p50 (Median): {p50:.2f}ms")
        print(f"p95:          {p95:.2f}ms")
        print(f"p99:          {p99:.2f}ms")
        print("--------------------")

        # Save results to JSON file
        results = {
            "test_config": {
                "url": args.url,
                "workers": args.workers,
                "duration": args.duration,
            },
            "summary": {
                "total_duration_s": round(total_time, 2),
                "total_requests": stats['total'],
                "successful_requests": stats['success'],
                "errored_requests": stats['errors'],
                "requests_per_second": round(stats['total'] / total_time, 2),
            },
            "latency_percentiles_ms": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        with open("tests/load_test_results.json", "w") as f:
            json.dump(results, f, indent=4)
        
        print("\nResults saved to tests/load_test_results.json")

if __name__ == "__main__":
    main()

