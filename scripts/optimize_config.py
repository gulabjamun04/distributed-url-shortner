import os

def generate_optimized_config():
    """
    Generates an optimized docker-compose.override.yml and prints optimization recommendations.
    """

    print("=== Optimization Recommendations Checklist ===")
    print("1. **Increase Uvicorn Workers:** For the 'app' service, `UVICORN_WORKERS` should generally be set to (2 * number of CPU cores) + 1. We're setting it to 4 as a robust starting point for many systems, but adjust based on your CPU cores.")
    print("2. **Increase Uvicorn Backlog:** `UVICORN_BACKLOG` is increased to 2048 to allow Uvicorn to queue more incoming connections, preventing connection drops under heavy load.")
    print("3. **Disable Debug Mode:** Ensure `DEBUG=false` in production to avoid performance overhead and security risks.")
    print("4. **Use High-Performance Event Loop & HTTP Parser:** Explicitly configuring `--loop uvloop` and `--http httptools` for Uvicorn leverages faster asynchronous I/O and HTTP parsing.")
    print("5. **Optimize PostgreSQL Connections and Buffers:** `max_connections` and `shared_buffers` are critical for PostgreSQL performance. Setting `max_connections=300` and `shared_buffers=256MB` provides a balanced configuration. Adjust `shared_buffers` to approximately 25% of the PostgreSQL container's allocated memory.")
    print("6. **Optimize Redis Memory and Client Limits:** `maxclients` is set to 10000 to handle a large number of concurrent Redis clients. `maxmemory` and `maxmemory-policy` are crucial to prevent Redis from consuming excessive RAM and to define eviction behavior when memory limits are reached (e.g., `allkeys-lru` for Least Recently Used eviction).")
    print("============================================")
    print("\nGenerating docker-compose.override.yml with optimizations...\n")

    optimized_yml_content = """
version: '3.8'
services:
  app:
    # --- FastAPI/Uvicorn Optimizations ---
    # UVICORN_WORKERS: Set to a value like (2 * number of CPU cores) + 1. '4' is a good starting point.
    # UVICORN_BACKLOG: Increases the number of queued connections Uvicorn will hold.
    # DEBUG: Must be 'false' for production performance.
    environment:
      - UVICORN_WORKERS=4
      - UVICORN_BACKLOG=2048
      - DEBUG=false
    # Command to run uvicorn with high-performance settings.
    # --loop uvloop: A much faster implementation of the asyncio event loop.
    # --http httptools: A faster HTTP parser.
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --workers 4
      --backlog 2048
      --loop uvloop
      --http httptools

  db-shard-0:
    # --- PostgreSQL Optimizations ---
    # max_connections: Allows more clients to connect. Default is 100.
    # shared_buffers: Sets memory for shared memory buffers. A good starting point is 25% of system memory.
    command: postgres -c max_connections=300 -c shared_buffers=256MB

  db-shard-1:
    command: postgres -c max_connections=300 -c shared_buffers=256MB

  db-shard-2:
    command: postgres -c max_connections=300 -c shared_buffers=256MB

  redis:
    # --- Redis Optimizations ---
    # maxclients: Increases the number of allowed concurrent clients.
    # maxmemory / maxmemory-policy: Sets a memory limit and an eviction policy to prevent Redis from consuming all system RAM.
    command: redis-server --maxclients 10000 --maxmemory 2gb --maxmemory-policy allkeys-lru
"""
    file_path = "docker-compose.override.yml"
    try:
        with open(file_path, "w") as f:
            f.write(optimized_yml_content.strip())
        print(f"Optimized configuration saved to {file_path}")
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")
        return

    print("\nInstructions: 'Run: docker-compose up -d to apply optimizations'")

if __name__ == "__main__":
    generate_optimized_config()
