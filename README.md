# Crucible: Semantic Cache & Reverse Proxy for LLM Inference

![Crucible](https://img.shields.io/badge/Crucible-Semantic%20Cache-brightgreen) ![License](https://img.shields.io/badge/License-MIT-blue) ![Python](https://img.shields.io/badge/Python-3.11%2B-blue)

**High-performance reverse proxy that intercepts, deduplicates, and caches semantically identical model queries—preventing wasted token compute, slashing API bills by 30–60%, and cutting latency to under 15ms.**

## The Problem

LLM inference is expensive, slow, and non-deterministic. Applications frequently pay full price and incur 1,000ms–3,000ms latency on user queries that are semantically identical (e.g., "How do I reset my password?" vs. "I forgot my password, how to reset?"). Standard exact-string caching (Redis key-value) achieves <5% cache hit rates on natural language.

## The Solution: Crucible

Crucible is the "pick and shovel" every production AI app needs: an intelligent gateway between your backend and upstream LLM providers. By adding semantic vector similarity matching and smart fallback routing, you immediately cut API costs by 30–60% and drop response latency to sub-20ms **without changing application logic**.

### Core Value Proposition

| Metric | Without Crucible | With Crucible |
|--------|------------------|---------------|
| Repeated / Semantic Query Cost | 100% full API rate | $0.00 (0 tokens) |
| Response Latency (Cache Hit) | 1,200ms – 3,500ms | < 15ms |
| Implementation Effort | Massive app refactoring | Change 1 line (`base_url`) |
| Provider Downtime Impact | App goes down / hangs | Instant fallback to secondary LLM |

---

## Quick Start

### Installation

```bash
# Via pip
pip install crucible-proxy

# Via Docker
docker run -p 8080:8080 -e UPSTREAM_KEY=sk-... ghcr.io/craftedwithintent/crucible:latest

# From source
git clone https://github.com/CraftedWithIntent/crucible.git
cd crucible
uv pip install -e .
```

### Basic Usage

#### 1. Start Crucible Proxy

```bash
crucible start --port 8080 --similarity 0.92
```

#### 2. Replace OPENAI_BASE_URL in Your App

**Before:**
```python
from openai import OpenAI

client = OpenAI(api_key="sk-...", base_url="https://api.openai.com/v1")
```

**After:**
```python
from openai import OpenAI

client = OpenAI(api_key="sk-...", base_url="http://localhost:8080/v1")
```

That's it. Cache hits are automatic.

#### 3. Monitor Cache Performance

```bash
crucible stats
```

Output:
```
Cache Statistics:
  Total Requests: 1,248
  Cache Hits: 742 (59.4%)
  Tokens Saved: 124,512
  Cost Saved: $3.74 USD
  Avg Latency (Hit): 8.2ms
  Avg Latency (Miss): 1,850ms
```

---

## Features

### MVP (Phase 1)

- ✅ **OpenAI-Compatible Gateway** — Drop-in proxy for `/v1/chat/completions` (streaming & non-streaming)
- ✅ **Hybrid Two-Tier Cache**:
  - **L1 Exact Match**: Fast SHA-256 hash lookup (<1ms)
  - **L2 Semantic Match**: Local embedding + cosine similarity (<15ms), configurable threshold (default 0.92)
- ✅ **Smart Fallback Routing** — Automatic failover to secondary API keys or providers (429/5xx errors)
- ✅ **Embedded Storage** — In-memory and SQLite-vec backends (zero external dependencies)
- ✅ **Streaming SSE Support** — Fully supports `stream: true` with zero latency overhead
- ✅ **CLI & Metrics** — Live dashboard with hit rates, token savings, and cost attribution
- ✅ **Docker & PyPI** — Single command deployment

### Roadmap

**Phase 2: Commercial Extensions**
- Crucible Cloud: Globally distributed edge-proxy network (Cloudflare workers, AWS Lambda@Edge)
- Centralized semantic cache sharing across microservices
- Real-time cost dashboards and FinOps attribution
- Smart invalidation hooks (tag-based, user-based, document-based)
- PII scrubbing before caching (regex + NER)
- Customer-managed encryption keys (CMEK)

**Phase 3: Enterprise**
- Multi-tenant rate limiting and budget guardrails
- Audit logging and compliance reports
- Private VPC deployments

---

## Architecture

### Functional Core / Imperative Shell

**Functional Core (Pure Logic):**
- Request normalization (system prompt stripping, whitespace canonicalization)
- Cosine similarity scoring & threshold evaluation
- Model fallback routing decisions
- Immutable types (CacheEntry, SimilarityScore, UpstreamRoute, CachedResponse)

**Imperative Shell (I/O & Transport):**
- FastAPI async HTTP server
- Async httpx streaming gateway (SSE reconstruction)
- Pluggable storage backends (in-memory, SQLite-vec, Redis, Qdrant)
- Prometheus metrics & OpenTelemetry exporter

### Request Flow

```
User App (OpenAI SDK)
    ↓
Crucible Proxy Server (FastAPI)
    ├─→ 1. Normalize Request
    │     └─→ Strip system prompt, canonicalize JSON
    ├─→ 2. L1 Exact Match (SHA-256 hash)
    │     └─→ Return cached response if found (< 1ms)
    ├─→ 3. L2 Semantic Match (embedding + cosine similarity)
    │     └─→ Return cached response if similarity >= 0.92 (< 15ms)
    ├─→ 4. Cache Miss → Route to Upstream Provider
    │     ├─→ OpenAI, Anthropic, Bedrock, Azure
    │     └─→ Handle streaming (SSE chunks) + fallback on 429/5xx
    ├─→ 5. Store Response in Cache
    │     ├─→ Generate embedding (local ONNX model)
    │     └─→ Persist to storage backend
    ├─→ 6. Return to User App
    │     └─→ Emit Prometheus metrics (hit_type, latency, tokens)
    ↓
User App receives response (cached or fresh)
```

### Codebase Layout

```
crucible/
├── .github/workflows/
│   ├── ci.yml                  # Test matrix (3.11/3.12), linting, build
│   └── publish.yml             # PyPI + Docker release
├── Dockerfile                  # Ultra-lightweight multi-stage image
├── pyproject.toml              # Build config, CLI entrypoint
├── README.md                   # This file
├── config/
│   └── crucible.yaml           # Default gateway config (thresholds, backends)
├── src/crucible/
│   ├── __init__.py             # Public API
│   ├── cli.py                  # Typer CLI (`crucible start`, `crucible stats`)
│   ├── domain/
│   │   └── types.py            # Immutable domain models (CacheEntry, Route, etc.)
│   ├── core/
│   │   ├── similarity.py       # Cosine similarity + threshold scoring
│   │   ├── normalizer.py       # Request normalization (exact match hashing)
│   │   └── router.py           # Fallback routing logic
│   └── infrastructure/
│       ├── server.py           # FastAPI routes (/v1/chat/completions)
│       ├── proxy_gateway.py    # Async HTTP + SSE streaming
│       ├── embeddings.py       # Local ONNX / FastEmbed generator
│       ├── storage/
│       │   ├── base.py         # Abstract storage interface
│       │   ├── memory.py       # In-memory backend
│       │   └── sqlite_vec.py   # SQLite-vec backend (Phase 1)
│       └── telemetry.py        # Prometheus + OpenTelemetry
└── tests/
    ├── test_similarity_core.py # Pure math unit tests
    ├── test_proxy_streaming.py # SSE chunk reconstruction
    └── test_benchmarks.py      # Latency (<15ms) performance tests
```

---

## Configuration

### crucible.yaml

```yaml
# Crucible gateway configuration

server:
  port: 8080
  host: "0.0.0.0"
  workers: 4

cache:
  # Similarity threshold (0.0–1.0)
  similarity_threshold: 0.92
  
  # Backend: memory, sqlite-vec, redis, qdrant
  backend: "memory"
  
  # Max entries to store (for memory backend)
  max_entries: 10000
  
  # Invalidation TTL (seconds, 0 = infinite)
  ttl_seconds: 3600

upstream:
  # Primary provider
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  
  # Fallback providers (attempted in order)
  fallback:
    - provider: "anthropic"
      api_key: "${ANTHROPIC_API_KEY}"
    - provider: "azure"
      api_key: "${AZURE_API_KEY}"
  
  # Request timeout
  timeout_seconds: 30
  
  # Retry policy
  max_retries: 3

telemetry:
  # Metrics export: prometheus, opentelemetry
  export: "prometheus"
  
  # Prometheus port
  metrics_port: 9090

logging:
  level: "info"  # debug, info, warning, error
```

---

## Performance Benchmarks

### Latency (P50/P99)

| Scenario | P50 Latency | P99 Latency | Notes |
|----------|------------|------------|-------|
| L1 Exact Match (hash lookup) | 0.8ms | 1.2ms | In-memory hash table |
| L2 Semantic Match (embedding + similarity) | 12ms | 18ms | ONNX model + cosine calc |
| Cache Miss → OpenAI | 1,200ms | 3,500ms | Upstream latency |
| **Savings per Cache Hit** | **99%** | **99%** | 1,200–3,500ms → <15ms |

### Token & Cost Savings

**Assumption:** 1,000 requests, 30% semantic cache hit rate (realistic for production apps)

| Metric | Without Cache | With Cache | Savings |
|--------|---------------|-----------|---------|
| Requests to Upstream | 1,000 | 700 | 300 (30%) |
| Tokens Consumed | 500,000 | 350,000 | 150,000 (30%) |
| Cost (GPT-4) | $15.00 | $10.50 | **$4.50 (30%)** |

---

## Deployment

### Local Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests --cov=src/crucible

# Start proxy
crucible start --port 8080 --similarity 0.92
```

### Docker

```bash
# Build locally
docker build -t crucible:latest .

# Run with environment variables
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=sk-... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  crucible:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crucible
  template:
    metadata:
      labels:
        app: crucible
    spec:
      containers:
      - name: crucible
        image: ghcr.io/craftedwithintent/crucible:latest
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: crucible-secrets
              key: openai-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

## Monetization & Commercial Tiers

### Free & Open Source (`crucible` binary)
- Local standalone proxy + Docker container
- Embedded local vector storage (SQLite-vec / in-memory)
- Exact & semantic caching, streaming support, Prometheus metrics
- **Use Case:** Dev/staging, self-hosted, edge deployments

### Crucible Cloud ($29–$149 / mo + $0.0005 per cached request)
- Global Edge Anycast: Sub-10ms cache lookups worldwide
- Centralized Dashboard: Hit-rate analytics, cost savings graphs
- Dynamic Cache Invalidation: By tag, user ID, collection
- **Use Case:** Production SaaS, multi-region apps, managed infrastructure

### Enterprise & Governance ($15K–$60K+ ACV)
- PII Sanitization: Redact sensitive data before caching
- Multi-Tenant FinOps: Per-team token budgets and rate caps
- Private VPC / Dedicated Single-Tenant: CMEK (bring your own encryption key)
- **Use Case:** Finance, healthcare, regulated industries

---

## Contributing

This is an open-source project. Contributions welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for your changes
4. Ensure `ruff check`, `pyright`, and `pytest` pass locally
5. Submit a PR with a clear description

---

## License

MIT License. See [LICENSE](LICENSE) for details.

**CraftedWithIntent™** — Built for precision. Built to scale.

---

## Questions? Support?

- 📖 [Documentation](https://docs.crucible.ai)
- 🐛 [GitHub Issues](https://github.com/CraftedWithIntent/crucible/issues)
- 💬 [Discord Community](https://discord.gg/crucible)
- 📧 [hello@craftedwithintent.ai](mailto:hello@craftedwithintent.ai)
