# 🔗 Distributed URL Shortener

A high-performance, production-grade URL shortening service built with FastAPI, PostgreSQL sharding, Redis caching, and Kafka event streaming. **Capable of handling 1,500+ requests per second** on commodity hardware.

[![Performance](https://img.shields.io/badge/RPS-1497-success)](./LOAD_TEST_RESULTS.md)
[![Latency](https://img.shields.io/badge/P99-228ms-success)](./LOAD_TEST_RESULTS.md)
[![Uptime](https://img.shields.io/badge/Uptime-100%25-success)](./LOAD_TEST_RESULTS.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

🌐 **Live Demo:** [api.distributed-url-shortner.online](https://api.distributed-url-shortner.online/)

---

## 🎯 Performance Results

| Metric             | v2 (Async)       | v1 (Threaded)   | Target  |
| ------------------ | ---------------- | --------------- | ------- |
| **Throughput**     | **1,497 RPS**    | 1,094 RPS       | 1,000+  |
| **Total Requests** | 90,000           | 11,026          | —       |
| **P50 Latency**    | 129ms            | 38ms            | <500ms  |
| **P99 Latency**    | 228ms            | 98ms            | <500ms  |
| **Cache Hit Rate** | 100%             | 100%            | >90%    |
| **Success Rate**   | 100%             | 100%            | >99%    |
| **Duration**       | 60s              | 10s             | —       |

> **v2** uses async `aiohttp` + `uvloop` (1,500 target RPS, 60s sustained). **v1** uses threaded `requests` (50 workers, 10s burst). Higher v2 throughput comes with proportionally higher latency under heavier load.

📊 **[View Full Load Test Results](./LOAD_TEST_RESULTS.md)**

---

## ✨ Features

### Core Functionality

- ⚡ **High-Performance Redirects** - Sub-230ms P99 latency under 1,500 RPS load
- 🔀 **Database Sharding** - Horizontal scalability via consistent hashing
- 💾 **Multi-Layer Caching** - Redis with look-aside + cache-null patterns
- 📊 **Real-Time Analytics** - Asynchronous click tracking via Kafka
- 🤖 **AI Classification** - Automatic URL categorization (HuggingFace)
- 🌐 **Production Deployment** - Cloudflare tunnel with zero-downtime

### Architecture

- **Application-Level Sharding:** 3 PostgreSQL nodes with uhashring
- **Event-Driven Analytics:** Decoupled via Redpanda (Kafka-compatible)
- **Observability:** Prometheus + Grafana with 10+ custom dashboards
- **Containerized:** Docker Compose orchestration (13+ services)

---

## 🏗️ Architecture Overview

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Cloudflare CDN │
└──────┬──────────┘
       │
       ▼
┌──────────────────┐         ┌─────────────┐
│   FastAPI App    │────────▶│ Redis Cache │
│  (4 workers)     │         └─────────────┘
└────────┬─────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              │
    ┌────────┐     ┌────────┐     ┌────────┐         │
    │ Shard0 │     │ Shard1 │     │ Shard2 │         │
    │  (PG)  │     │  (PG)  │     │  (PG)  │         │
    └────────┘     └────────┘     └────────┘         │
                                                      │
         ┌────────────────────────────────────────────┘
         │
         ▼
    ┌──────────┐        ┌──────────────┐
    │ Redpanda │───────▶│ Analytics    │
    │  (Kafka) │        │  Worker      │
    └──────────┘        └──────────────┘
         │              ┌──────────────┐
         └─────────────▶│ Classifier   │
                        │  Worker      │
                        └──────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- 8GB RAM minimum (recommended: 16GB)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/gulabjamun04/distributed-url-shortner.git
cd distributed-url-shortener
```

2. **Start all services**

```bash
docker-compose up -d
```

3. **Wait for services to be ready** (~30 seconds)

```bash
docker-compose ps
# All services should show "Up"
```

4. **Seed the database** (5,000 URLs)

```bash
python scripts/seed_db.py
```

5. **Access the application**

- App: http://localhost:8000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

---

## 📊 Monitoring & Dashboards

### Grafana Dashboards

Access at `http://localhost:3000`:

- **FastAPI Performance:** RPS, latency percentiles, error rates
- **Database Metrics:** Connection pools, query duration, shard distribution
- **Cache Analytics:** Hit/miss rates, memory usage
- **System Health:** CPU, memory, network I/O

### Prometheus Targets

- FastAPI app: `app:8000/metrics`
- Worker: `worker:8001/metrics`
- PostgreSQL (3x): `postgres-exporter-{0,1,2}:9187`
- Redis: `redis-exporter:9121`
- Redpanda: `redpanda:9644`

---

## 🧪 Load Testing

### Run Performance Tests

1. **Warm up the cache**

```bash
python scripts/warmup_cache.py --url http://localhost:8000
```

2. **Run load test (async — recommended)**

```bash
python tests/load_generator.py --url http://localhost:8000 --rps 1500 --duration 60
```

3. **Or run threaded load test (legacy)**

```bash
python tests/stress_test.py --url http://localhost:8000 --workers 300 --duration 60
```

4. **View results**

```bash
python scripts/analyze_results.py
```

### Expected Results

| Metric         | Async (`load_generator.py`) | Threaded (`stress_test.py`) |
| -------------- | --------------------------- | --------------------------- |
| **RPS**        | 1,200-1,500                 | 800-1,100                   |
| **P50 Latency**| 100-150ms                   | 30-50ms                     |
| **P99 Latency**| 200-300ms                   | 80-100ms                    |
| **Error Rate** | <1%                         | <1%                         |

---

## 🛠️ Tech Stack

| Layer              | Technology                     | Purpose                          |
| ------------------ | ------------------------------ | -------------------------------- |
| **Application**    | FastAPI, Python 3.14           | Async API framework              |
| **Database**       | PostgreSQL 16 (Alpine)         | Sharded persistent storage       |
| **Cache**          | Redis 7 (Alpine)               | High-speed in-memory cache       |
| **Messaging**      | Redpanda                       | Kafka-compatible event streaming |
| **Load Balancing** | Consistent Hashing (uhashring) | Request distribution             |
| **Monitoring**     | Prometheus + Grafana           | Metrics & visualization          |
| **Deployment**     | Docker Compose                 | Container orchestration          |
| **CDN**            | Cloudflare Tunnel              | Public access & caching          |
| **AI/ML**          | HuggingFace Transformers       | URL classification               |

---

## 📁 Project Structure

```
distributed-url-shortener/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── db.py                # Database connections
│   ├── services/
│   │   ├── cache.py         # Redis caching logic
│   │   └── producer.py      # Kafka event producer
│   ├── utils/
│   │   └── hashing.py       # Consistent hashing
│   └── templates/
│       └── index.html       # Frontend UI
├── worker/
│   ├── analytics.py         # Click tracking consumer
│   └── classifier.py        # AI URL categorization
├── scripts/
│   ├── seed_db.py           # Database seeder
│   ├── diagnose.py          # System health check
│   └── warmup_cache.py      # Cache pre-loader
├── grafana/
│   └── provisioning/        # Dashboard configs
│       ├── dashboards/
│       │   ├── dashboard.yml
│       │   ├── fastapi_performance_dashboard.json
│       │   └── load_test_dashboard.json
│       └── datasources/
│           └── datasource.yml
├── monitoring/
├── prometheus/
│   └── prometheus.yml       # Monitoring config
├── tests/
│   ├── load_generator.py    # Async load test (aiohttp + uvloop)
│   ├── stress_test.py       # Threaded load test (requests)
│   ├── load_test_results.json
│   └── requirements.txt
└── docker-compose.yml       # Service orchestration
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
# Database
DB_SHARD_0_URL=postgresql+asyncpg://user:password@db-shard-0:5432/url_shortener
DB_SHARD_1_URL=postgresql+asyncpg://user:password@db-shard-1:5432/url_shortener
DB_SHARD_2_URL=postgresql+asyncpg://user:password@db-shard-2:5432/url_shortener

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=redpanda:29092

# Cloudflare (optional)
TUNNEL_TOKEN=your_tunnel_token_here
```

### Performance Tuning

Edit `docker-compose.override.yml`:

```yaml
services:
  app:
    environment:
      - UVICORN_WORKERS=6
      - UVICORN_BACKLOG=4096
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --workers 6
      --loop uvloop
      --http httptools
```

---

## 📈 Scaling Guide

### Horizontal Scaling

1. **Add Database Shards**
   - Update `SHARD_ENGINES` in `app/db.py`
   - Add service in `docker-compose.yml`
   - Re-run migration

2. **Increase Workers**
   - Modify `UVICORN_WORKERS` (1 worker per CPU core)

3. **Redis Cluster** (for production)
   - Replace standalone Redis with Redis Cluster
   - Update `cache.py` for cluster mode

### Vertical Scaling

- Increase PostgreSQL `shared_buffers` to 25% of RAM
- Increase connection pool sizes
- Allocate more memory to Redis (`maxmemory` config)

---

## Screenshots

### 1. Terminal Load Test - 1,497 RPS Achievement (v2 Async)

![Terminal 1497 RPS](screenshots/terminal_1094_rps.png)


### 2. Grafana - Total RPS Dashboard

![Grafana Total RPS](screenshots/grafana_total_rps.png)


### 3. Grafana - P99 Latency

![Grafana P99 Latency](screenshots/grafana_latency_p99.png)


### 4. Grafana - P50 Latency (2.7ms)

![Grafana P50 Latency](screenshots/grafana_latency_p50.png)


### 5. Grafana - Redis Hit Rate (100%)

![Redis Hit Rate](screenshots/grafana_redis_hit_rate.png)


### 6. Prometheus - All Targets UP

![Prometheus Targets](screenshots/prometheus_targets.png)


### 7. Production Application

![Production Interface](screenshots/production_app_interface.png)


## 🐛 Troubleshooting

### Common Issues

**Issue:** Low RPS (<500)

```bash
# Check worker count
docker-compose logs app | grep workers

# Increase workers in docker-compose.override.yml
UVICORN_WORKERS=8
```

**Issue:** High latency

```bash
# Check cache hit rate
python scripts/diagnose.py

# Warm up cache if needed
python scripts/warmup_cache.py
```

**Issue:** Connection errors

```bash
# Check all services are up
docker-compose ps

# Restart if needed
docker-compose restart
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- FastAPI for the excellent async framework
- Redpanda for Kafka-compatible messaging
- HuggingFace for transformer models
- Grafana Labs for visualization tools

---

## 📞 Contact

**Project Link:** [github.com/yourusername/distributed-url-shortener](https://github.com/gulabjamun04/distributed-url-shortner)

**Live Demo:** [api.distributed-url-shortner.online](https://api.distributed-url-shortner.online/)

---

<div align='center'>
<b>⭐ Star this repo if you found it helpful!</b>
</div>
