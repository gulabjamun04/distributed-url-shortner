import subprocess
import json
import requests
import time
import sys
import re

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# List to keep track of issues found
issues = []


def run_command(command, shell=True, capture_output=True, text=True, check=False):
    """Helper function to run shell commands."""
    try:
        result = subprocess.run(
            command, shell=shell, capture_output=capture_output, text=text, check=check, timeout=10)
        return result
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="Command timed out", stderr="")
    except FileNotFoundError:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout=f"Command not found: {command}", stderr="")
    except Exception as e:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout=f"An error occurred: {e}", stderr="")


def run_docker_exec_command(service_name, command, capture_output=True, text=True):
    """Helper function to run commands inside a Docker container."""
    docker_command = f"docker compose exec {service_name} {command}"
    return run_command(docker_command, capture_output=capture_output, text=text)


def check_redis():
    print("Checking Redis health...")
    try:
        ping_result = run_docker_exec_command("redis", "redis-cli ping")
        if "PONG" in ping_result.stdout:
            print(f"  {GREEN}✓ Redis is UP{RESET}")
        else:
            print(f"  {RED}✗ Redis is DOWN: {ping_result.stdout.strip()}{RESET}")
            issues.append("Redis is DOWN")
            return

        info_result = run_docker_exec_command("redis", "redis-cli info stats")
        if info_result.returncode == 0:
            stats = {}
            for line in info_result.stdout.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    stats[key.strip()] = value.strip()

            total_keys_result = run_docker_exec_command("redis", "redis-cli dbsize")
            total_keys = total_keys_result.stdout.strip() if total_keys_result.returncode == 0 else "N/A"

            memory_result = run_docker_exec_command("redis", "redis-cli info memory")
            memory_info = {}
            if memory_result.returncode == 0:
                for line in memory_result.stdout.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        memory_info[key.strip()] = value.strip()

            hit_rate = "N/A"
            if 'keyspace_hits' in stats and 'keyspace_misses' in stats:
                hits = int(stats['keyspace_hits'])
                misses = int(stats['keyspace_misses'])
                if (hits + misses) > 0:
                    hit_rate = f"{(hits / (hits + misses) * 100):.2f}%"

            used_memory_human = memory_info.get('used_memory_human', 'N/A')

            print(f"    Hit Rate: {hit_rate}, Total Keys: {total_keys}, Memory Usage: {used_memory_human}")
        else:
            print(f"  {YELLOW}WARNING: Could not get Redis stats: {info_result.stderr.strip()}{RESET}")

    except Exception as e:
        print(f"  {RED}✗ Redis check failed: {e}{RESET}")
        issues.append("Redis check failed")


def check_databases():
    print("Checking PostgreSQL databases health...")
    db_services = ["db-shard-0", "db-shard-1", "db-shard-2"]
    total_urls = 0
    
    for i, service_name in enumerate(db_services):
        try:
            # Check connection and get URL count
            count_cmd = f"psql -U user -d url_shortener -c 'SELECT count(*) FROM urls'"
            count_result = run_docker_exec_command(service_name, count_cmd)
            
            if count_result.returncode == 0 and "count" in count_result.stdout:
                count_match = re.search(r'\s*(\d+)\s*', count_result.stdout.splitlines()[-2])
                url_count = int(count_match.group(1)) if count_match else 0
                total_urls += url_count
                print(f"  {GREEN}✓ Shard {i+1} ({service_name}): {url_count} URLs{RESET}")

                # Check active connections
                conn_cmd = f"psql -U user -d url_shortener -c 'SELECT count(*) FROM pg_stat_activity'"
                conn_result = run_docker_exec_command(service_name, conn_cmd)
                if conn_result.returncode == 0 and "count" in conn_result.stdout:
                    conn_count_match = re.search(r'\s*(\d+)\s*', conn_result.stdout.splitlines()[-2])
                    conn_count = int(conn_count_match.group(1)) if conn_count_match else 0
                    print(f"    Active Connections: {conn_count}")
                else:
                    print(f"  {YELLOW}WARNING: Could not get active connections for Shard {i+1}{RESET}")
            else:
                print(f"  {RED}✗ Shard {i+1} ({service_name}): DOWN - {count_result.stderr.strip() or count_result.stdout.strip()}{RESET}")
                issues.append(f"Database Shard {i+1} is DOWN")

        except Exception as e:
            print(f"  {RED}✗ Shard {i+1} ({service_name}) check failed: {e}{RESET}")
            issues.append(f"Database Shard {i+1} check failed")
    
    print(f"  Total URLs across all shards: {total_urls}")

def check_kafka():
    print("Checking Kafka (Redpanda) health...")
    try:
        metrics_result = requests.get("http://localhost:9644/metrics", timeout=5)
        if metrics_result.status_code == 200:
            print(f"  {GREEN}✓ Kafka (Redpanda) is UP{RESET}")
        else:
            print(f"  {RED}✗ Kafka (Redpanda) is DOWN (Status: {metrics_result.status_code}){RESET}")
            issues.append("Kafka (Redpanda) is DOWN")
    except requests.exceptions.RequestException as e:
        print(f"  {RED}✗ Kafka (Redpanda) check failed: {e}{RESET}")
        issues.append("Kafka (Redpanda) check failed")

def check_prometheus():
    print("Checking Prometheus health...")
    try:
        query_url = "http://localhost:9090/api/v1/query?query=up"
        response = requests.get(query_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                print(f"  {GREEN}✓ Prometheus is UP{RESET}")
                targets_up = []
                targets_down = []
                for result in data["data"]["result"]:
                    target_name = result["metric"].get("instance", "unknown")
                    status = result["value"][1]
                    if status == "1":
                        targets_up.append(target_name)
                    else:
                        targets_down.append(target_name)
                
                print(f"    Targets UP: {', '.join(targets_up) if targets_up else 'None'}")
                if targets_down:
                    print(f"    {RED}✗ Targets DOWN: {', '.join(targets_down)}{RESET}")
                    issues.append(f"Prometheus targets down: {', '.join(targets_down)}")
            else:
                print(f"  {RED}✗ Prometheus query failed: {data['error']}{RESET}")
                issues.append("Prometheus query failed")
        else:
            print(f"  {RED}✗ Prometheus is DOWN (Status: {response.status_code}){RESET}")
            issues.append("Prometheus is DOWN")
    except requests.exceptions.RequestException as e:
        print(f"  {RED}✗ Prometheus check failed: {e}{RESET}")
        issues.append("Prometheus check failed")

def check_app_latency():
    print("Checking FastAPI application latency...")
    latencies = []
    app_url = "http://localhost:8000/metrics" # Using a lightweight endpoint
    num_requests = 10

    for _ in range(num_requests):
        try:
            start_time = time.time()
            response = requests.get(app_url, timeout=5)
            end_time = time.time()
            if response.status_code == 200:
                latencies.append((end_time - start_time) * 1000) # in ms
            else:
                print(f"  {YELLOW}WARNING: App returned status {response.status_code} for {app_url}{RESET}")
                # Don't add to latencies, but don't fail the check
        except requests.exceptions.RequestException as e:
            print(f"  {RED}✗ App latency check failed for {app_url}: {e}{RESET}")
            issues.append("FastAPI app is unreachable or unhealthy")
            return # Exit early if app is not reachable

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"  App latency: {avg_latency:.2f}ms")
        if avg_latency > 100:
            print(f"  {YELLOW}WARNING - App is slow (Average latency > 100ms){RESET}")
            issues.append(f"FastAPI app is slow (Avg latency: {avg_latency:.2f}ms)")
    else:
        print(f"  {RED}✗ Could not measure app latency (No successful requests){RESET}")
        issues.append("Could not measure FastAPI app latency")

def check_cache_hit_rate():
    print("Checking Cache Hit Rate...")
    try:
        # Query Prometheus for Redis hit and miss cumulative counts
        prometheus_url = "http://localhost:9090/api/v1/query"
        
        hits_query = "redis_keyspace_hits_total"
        misses_query = "redis_keyspace_misses_total"

        hits_response = requests.get(prometheus_url, params={'query': hits_query}, timeout=5)
        misses_response = requests.get(prometheus_url, params={'query': misses_query}, timeout=5)

        hits_data = hits_response.json()
        misses_data = misses_response.json()

        hits = 0
        if hits_data["status"] == "success" and hits_data["data"]["result"]:
            hits = float(hits_data["data"]["result"][0]["value"][1])
        
        misses = 0
        if misses_data["status"] == "success" and misses_data["data"]["result"]:
            misses = float(misses_data["data"]["result"][0]["value"][1])

        if (hits + misses) > 0:
            hit_rate = (hits / (hits + misses)) * 100
            print(f"  Cache hit rate: {hit_rate:.2f}%")
            if hit_rate < 80:
                print(f"  {YELLOW}WARNING - Low cache efficiency (Hit rate < 80%){RESET}")
                issues.append(f"Low cache efficiency (Hit rate: {hit_rate:.2f}%)")
        elif hits == 0 and misses == 0:
            print(f"  Cache hit rate: 0.00% (No cache activity detected){RESET}")
        else:
            print(f"  {YELLOW}WARNING: No Redis hit/miss metrics available from Prometheus.{RESET}")
            issues.append("No Redis hit/miss metrics from Prometheus")

    except requests.exceptions.RequestException as e:
        print(f"  {RED}✗ Cache hit rate check failed: {e}{RESET}")
        issues.append("Cache hit rate check failed")
    except json.JSONDecodeError:
        print(f"  {RED}✗ Cache hit rate check failed: Invalid JSON response from Prometheus.{RESET}")
        issues.append("Cache hit rate check failed (Invalid JSON)")

def main():
    print(f"""
{GREEN}=== System Health Check ==={RESET}
""")
    
    # Run all checks
    check_redis()
    print("-" * 30)
    check_databases()
    print("-" * 30)
    check_kafka()
    print("-" * 30)
    check_prometheus()
    print("-" * 30)
    check_app_latency()
    print("-" * 30)
    check_cache_hit_rate()
    print("-" * 30)

    print(f"""
--- Summary ---""")
    if not issues:
        print(f"{GREEN}✓ All systems operational{RESET}")
    else:
        print(f"{RED}✗ Issues detected:{RESET}")
        for issue in issues:
            print(f"  - {issue}")
        print("""
Recommendations: Review logs for affected services and ensure all Docker containers are running.""")

if __name__ == "__main__":
    main()
