#!/bin/bash
set -e

# 2. Print banner
echo '================================='
echo '  URL Shortener Load Test Suite'
echo '================================='

# 3. Check prerequisites
echo 'Checking prerequisites...'
docker-compose ps | grep -q 'Up' || { echo 'Error: Docker services are not running. Please start them with "docker-compose up -d".'; exit 1; }
test -f data/benchmark_keys.txt || { echo 'Error: data/benchmark_keys.txt not found. Please create it.'; exit 1; }
curl -s http://localhost:3000 > /dev/null || { echo 'Error: Grafana is not accessible at http://localhost:3000. Please ensure it is running.'; exit 1; }
echo 'Prerequisites met.'
echo ''

# 4. Run diagnostics
echo 'Running pre-flight checks...'
python scripts/diagnose.py
echo ''

# 5. Warmup phase
echo 'Warming up cache...'
python scripts/warmup_cache.py --url http://localhost:8000
echo 'Cache warmed. Waiting 30 seconds...'
sleep 30

# 6. Open monitoring (if on macOS)
echo 'Opening monitoring dashboards...'
open http://localhost:3000 2>/dev/null || echo 'Open http://localhost:3000 manually'
open http://localhost:9090 2>/dev/null || echo 'Open http://localhost:9090 manually'

# 7. Countdown
echo 'Starting load test in:'
for i in 3 2 1; do echo "$i"...; sleep 1; done
echo 'GO!'

# 8. Run test
python tests/stress_test.py --url http://localhost:8000 --workers 300 --duration 60

# 9. Post-test
echo ''
echo 'Test complete! Analyzing results...'
sleep 5
python scripts/analyze_results.py

# 10. Print next steps
echo ''
echo 'Next steps:'
echo '1. Take screenshots of Grafana dashboard'
echo '2. Check tests/load_test_results.json for detailed metrics'
echo '3. Review LOAD_TEST_RESULTS.md and update with your numbers'
