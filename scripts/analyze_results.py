import json
import matplotlib.pyplot as plt
import statistics
import sys


def analyze_results(results_file="tests/load_test_results.json", plot_file="tests/results_chart.png"):
    try:
        with open(results_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Results file not found at {results_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {results_file}")
        sys.exit(1)

    # Extracting data
    test_config = data.get("test_config", {})
    summary = data.get("summary", {})
    latency_percentiles = data.get("latency_percentiles_ms", {})

    duration = test_config.get("duration", 0)
    total_requests = summary.get("total_requests", 0)
    successful_requests = summary.get("successful_requests", 0)
    errored_requests = summary.get("errored_requests", 0)
    average_rps = summary.get("requests_per_second", 0)

    p50_latency = latency_percentiles.get("p50", 0)
    p95_latency = latency_percentiles.get("p95", 0)
    p99_latency = latency_percentiles.get("p99", 0)

    # Calculations
    if total_requests > 0:
        success_rate_percent = (successful_requests / total_requests) * 100
        error_rate_percent = (errored_requests / total_requests) * 100
    else:
        success_rate_percent = 0
        error_rate_percent = 0

    # For Peak and Sustained RPS, we only have average RPS from current stress_test.py
    # A real load test would capture RPS over time to calculate these accurately.
    peak_rps = average_rps
    sustained_rps = average_rps

    # Print Summary Report
    print("=== Load Test Results ===")
    print(f"Duration: {duration} seconds")
    print(f"Total Requests: {total_requests}")
    print(f"Average RPS: {average_rps:.0f}")
    print(
        f"Peak RPS: {peak_rps:.0f} (Note: Derived from average RPS due to data limitations)")
    print(
        f"Sustained RPS: {sustained_rps:.0f} (Note: Derived from average RPS due to data limitations)")
    print("---")
    print("Latency:")
    print(f"  P50: {p50_latency:.1f}ms")
    print(f"  P95: {p95_latency:.1f}ms")
    print(f"  P99: {p99_latency:.1f}ms")
    print("---")
    print(f"Success Rate: {success_rate_percent:.1f}%")
    print(f"Errors: {errored_requests} ({error_rate_percent:.1f}%)")
    # Error breakdown by status code is not available in current load_test_results.json
    print("  (Error breakdown by status code not available)")
    print("---")

    # Pass/Fail Criteria
    overall_status = True

    # RPS check
    if average_rps >= 1000:
        print(f"✓ PASSED: RPS > 1000")
    else:
        print(f"✗ FAILED: RPS < 1000 (Current: {average_rps:.0f})")
        overall_status = False

    # P99 Latency check
    if p99_latency < 500:  # in ms
        print(f"✓ PASSED: P99 < 500ms")
    else:
        print(f"✗ FAILED: P99 >= 500ms (Current: {p99_latency:.1f}ms)")
        overall_status = False

    # Error rate check
    if error_rate_percent < 1:
        print(f"✓ PASSED: Error rate < 1%")
    else:
        print(
            f"✗ FAILED: Error rate >= 1% (Current: {error_rate_percent:.1f}%)")
        overall_status = False

    print("RESULT: ", end="")
    if overall_status:
        print("ALL TARGETS MET 🎉")
    else:
        print("ISSUES DETECTED 🔴")

    # Generate Plot (Status Code Distribution Pie Chart)
    if total_requests > 0:
        labels = ['Success', 'Errors']
        sizes = [successful_requests, errored_requests]
        colors = ['#4CAF50', '#F44336']  # Green for Success, Red for Errors
        explode = (0.1, 0)  # explode 1st slice

        fig1, ax1 = plt.subplots()
        ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                shadow=True, startangle=90)
        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax1.axis('equal')
        plt.title('Request Status Distribution')
        plt.savefig(plot_file)
        print(f"Plot saved to {plot_file}")
    else:
        print("Skipping plot generation: No requests processed.")


if __name__ == "__main__":
    analyze_results()
