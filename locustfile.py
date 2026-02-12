from locust import HttpUser, task, between
import random
import os

class URLShortenerUser(HttpUser):
    wait_time = between(1, 2.5)  # Simulate user think time between requests

    host = "http://localhost:8000"  # Default host for testing locally

    # Ensure benchmark_keys.txt exists in the data directory
    benchmark_keys_file = "data/benchmark_keys.txt"
    short_codes = []

    def on_start(self):
        """On start, load short codes from the benchmark_keys.txt file."""
        if not os.path.exists(self.benchmark_keys_file):
            print(f"Error: {self.benchmark_keys_file} not found. Please run seed_db.py first.")
            return

        with open(self.benchmark_keys_file, "r") as f:
            self.short_codes = [line.strip() for line in f if line.strip()]
        
        if not self.short_codes:
            print(f"Warning: No short codes found in {self.benchmark_keys_file}.")

    @task(10) # Higher weight for accessing shortened URLs
    def view_shortened_url(self):
        """Task to simulate users accessing a shortened URL."""
        if self.short_codes:
            short_code = random.choice(self.short_codes)
            self.client.get(f"/{short_code}", name="/[short_code]")
        else:
            print("No short codes available to view.")

    @task(1) # Lower weight for shortening new URLs
    def shorten_new_url(self):
        """Task to simulate users shortening a new URL."""
        long_url = f"http://example.com/some/long/path/{random.randint(100000, 999999)}"
        self.client.post("/shorten", data={"long_url": long_url}, name="/shorten")
