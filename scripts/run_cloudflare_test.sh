#!/bin/bash
set -e

# 2. Set TARGET_URL variable
TARGET_URL='https://api.distributed-url-shortner.online'

# 3. Print banner
echo '======================================='
echo '  Cloudflare Production Load Test'
echo "  Target: $TARGET_URL"
echo '======================================='

# 4. Verify Cloudflare is active
echo 'Checking Cloudflare tunnel...'
curl -sI "$TARGET_URL" | grep -q 'cf-ray' && echo '✓ Cloudflare is active' || echo '✗ Cloudflare not detected'
echo ''

# 5. Test basic connectivity
echo 'Testing connectivity...'
curl -sI "$TARGET_URL" | head -n 1
echo ''

# 6. Warmup cache
echo 'Warming up production cache...'
python scripts/warmup_cache.py --url "$TARGET_URL"
sleep 10
echo ''

# 7. Run load test
echo 'Starting production load test...'
echo 'Note: Cloudflare adds ~10-30ms latency (expected)'
echo 'Target: 800+ RPS is excellent for production'
echo ''
python tests/stress_test.py --url "$TARGET_URL" --workers 300 --duration 60

# 8. Analyze results
sleep 5
python scripts/analyze_results.py

# 9. Print notes
echo ''
echo 'Production Test Notes:'
echo '- Cloudflare latency overhead: Normal'
echo '- 800+ RPS on Cloudflare = 1000+ RPS on localhost'
echo '- Cache hit rate should be high (>90%)'
