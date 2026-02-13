import os

# --- YAML content for docker-compose.override.yml ---
# This override file applies performance tuning settings without modifying the base docker-compose.yml
# It's a best practice for separating development/production configurations.
OPTIMIZED_YAML_CONTENT = """
version: '3.8'
services:
  app:
    # --- FastAPI/Uvicorn Optimizations ---
    # UVICORN_WORKERS: Set to a value like 2x the number of CPU cores. '4' is a good starting point.
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

def print_optimization_checklist():
    """Prints a checklist of optimization recommendations."""
    print("--- Performance Optimization Checklist ---")
    print("\n[ App Service (FastAPI/Uvicorn) ]")
    print("  ✓ Increased Uvicorn workers to 4 for parallel request handling.")
    print("  ✓ Set TCP backlog to 2048 to handle more incoming connections.")
    print("  ✓ Switched to 'uvloop' and 'httptools' for faster event loop and HTTP parsing.")
    print("  ✓ Disabled debug mode for production performance.")
    
    print("\n[ PostgreSQL Services ]")
    print("  ✓ Increased max_connections to 300 per shard.")
    print("  ✓ Allocated 256MB of shared_buffers for better query performance.")

    print("\n[ Redis Service ]")
    print("  ✓ Increased maxclients to 10,000.")
    print("  ✓ Set a 2GB memory limit with 'allkeys-lru' eviction policy.")
    print("-" * 40)

def generate_override_file():
    """Generates the docker-compose.override.yml file."""
    print("\nGenerating 'docker-compose.override.yml'...")
    try:
        with open('docker-compose.override.yml', 'w') as f:
            f.write(OPTIMIZED_YAML_CONTENT)
        print("Successfully created 'docker-compose.override.yml'")
    except Exception as e:
        print(f"Error generating file: {e}")

def main():
    """Main function to run the optimization script."""
    print_optimization_checklist()
    generate_override_file()
    print("\n--- Instructions ---")
    print("Run the following command to apply the new optimizations:")
    print("  docker-compose up -d")
    print("-" * 40)

if __name__ == "__main__":
    main()
