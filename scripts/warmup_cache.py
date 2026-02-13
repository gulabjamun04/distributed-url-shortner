import requests
import threading
import argparse
import sys
import time
from typing import List

# A shared counter for progress tracking
progress_counter = 0
progress_lock = threading.Lock()
last_print_time = time.time()

def warmup_worker(keys_subset: List[str], target_url: str):
    """
    Worker function to send GET requests for a subset of keys.
    """
    global progress_counter, last_print_time
    
    for key in keys_subset:
        url = f'{target_url}/{key}'
        try:
            requests.get(url, timeout=5, allow_redirects=False)
        except requests.RequestException:
            # Silently ignore connection errors, 404s, etc.
            pass
        
        with progress_lock:
            progress_counter += 1
            current_time = time.time()
            # Print progress every 500 keys or every 0.2 seconds
            if progress_counter % 500 == 0 or (current_time - last_print_time) > 0.2:
                sys.stdout.write(f"\rWarming up {progress_counter}/{len(keys)}...")
                sys.stdout.flush()
                last_print_time = current_time

def main():
    """
    Main function to orchestrate the cache warmup process.
    """
    parser = argparse.ArgumentParser(description="Cache warmup script for the URL shortener.")
    parser.add_argument("--url", default="http://localhost:8000", help="The target URL of the application.")
    args = parser.parse_args()

    print("Starting cache warmup...")

    try:
        with open("data/benchmark_keys.txt", "r") as f:
            global keys
            keys = [line.strip() for line in f if line.strip()]
        if not keys:
            print("Error: data/benchmark_keys.txt is empty or not found.")
            return
    except FileNotFoundError:
        print("Error: data/benchmark_keys.txt not found.")
        return

    num_threads = 10
    chunk_size = (len(keys) + num_threads - 1) // num_threads  # Ceiling division
    key_chunks = [keys[i:i + chunk_size] for i in range(0, len(keys), chunk_size)]

    threads = []
    
    for chunk in key_chunks:
        thread = threading.Thread(target=warmup_worker, args=(chunk, args.url))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()
        
    sys.stdout.write(f"\rWarmed up {progress_counter}/{len(keys)}... Done.\n")
    sys.stdout.flush()
    
    print(f"Cache warmup complete. Processed {progress_counter} URLs. Redis is hot!")

if __name__ == "__main__":
    main()
