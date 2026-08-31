# Prospect AI: Semantic Cache & Reverse Proxy for LLM Inference

![Prospect AI](https://img.shields.io/badge/Prospect%20AI-Semantic%20Cache-brightgreen) ![License](https://img.shields.io/badge/License-MIT-blue) ![Python](https://img.shields.io/badge/Python-3.11%2B-blue)

**High-performance reverse proxy that intercepts, deduplicates, and caches semantically identical model queries—preventing wasted token compute and cutting latency to under 15ms.**

## What is Prospect AI?

Prospect AI is an intelligent gateway (reverse proxy) between your LLM applications and upstream providers (OpenAI, Anthropic, etc.). It combines two-tier semantic caching (exact-match + embedding-based similarity) with smart fallback routing to reduce costs, improve latency, and ensure high availability.

### Problem

LLM inference is expensive and slow. Applications pay full token costs even for semantically duplicate queries (e.g., "How do I reset my password?" vs. "I forgot my password, how to reset?"). Standard key-value caches achieve <5% hit rates on natural language. Meanwhile, 429/5xx errors cause app crashes without fallback providers.

## Quick Start

### Installation

```bash
# Via pip
pip install prospect-ai

# Via Docker
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/craftedwithintent/prospect-ai:latest

# From source
git clone https://github.com/CraftedWithIntent/prospect-ai.git
cd prospect-ai
pip install -e .
```

### Basic Usage

#### 1. Start Prospect AI Proxy

```bash
prospect-ai start --port 8000 --similarity 0.92
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

client = OpenAI(api_key="sk-...", base_url="http://localhost:8000/v1")
```

That's it. Cache hits are automatic.

#### 3. Monitor Cache Performance

```bash
prospect-ai stats
```

Output:
```
Cache Statistics:
  Total Requests: 1,248
  Cache Hits: 742 (59.4%)
  Avg Latency (Hit): 8.2ms
  Avg Latency (Miss): 1,850ms
  Cost Saved: $18.50
```

---

## Build Your First Cached LLM App

Prospect AI shines as a drop-in reverse proxy for any LLM application. Here's a complete example:

### Example: Chat Service with Semantic Caching

A FastAPI service that uses Prospect to cache LLM responses:

**1. Start Prospect proxy (Terminal 1)**

```bash
prospect-ai start --port 8000 --similarity 0.92
```

**2. Create chat service (`app.py`)**

```python
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel
import time

app = FastAPI()

# Point to Prospect proxy instead of OpenAI directly
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-openai-api-key"
)

class Message(BaseModel):
    content: str

@app.post("/chat")
def chat(message: Message):
    """Chat endpoint that automatically benefits from Prospect caching."""
    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message.content}],
    )
    latency = int((time.time() - start) * 1000)
    
    return {
        "response": response.choices[0].message.content,
        "latency_ms": latency,
        "tokens_used": response.usage.completion_tokens,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
```

**3. Run and test (Terminal 2)**

```bash
pip install fastapi uvicorn openai
python app.py

# In Terminal 3, test:
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "What is machine learning?"}'

# First request: ~2 seconds (upstream to OpenAI)
# {"response": "Machine learning is...", "latency_ms": 2150, "tokens_used": 125}

# Similar follow-up: ~15ms (cache hit!)
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "Tell me about machine learning"}'

# {"response": "Machine learning is...", "latency_ms": 12, "tokens_used": 0}
```

### Full Working Example

A complete, production-ready example with metrics and tests is in **[examples/llm-chat-with-caching/](examples/llm-chat-with-caching/)**:

- ✅ Full `app.py` with error handling and logging
- ✅ Real-time cache metrics endpoint
- ✅ Cost calculation and savings tracking
- ✅ Comprehensive test suite (14 tests)
- ✅ Docker + Kubernetes deployment
- ✅ Detailed `README.md` with architecture and troubleshooting

**Clone and run locally:**

```bash
cd examples/llm-chat-with-caching
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key-here"

# Terminal 1: Start Prospect
prospect-ai start --port 8000

# Terminal 2: Start chat app
python app.py

# Terminal 3: Make requests
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "What is AI?"}'
```

See [examples/README.md](examples/README.md) for more examples and use cases.

---

## Features

### MVP (v1.0.0 Complete)

- ✅ **OpenAI-Compatible Gateway** — Drop-in proxy for `/v1/chat/completions` (streaming & non-streaming)
- ✅ **Hybrid Two-Tier Cache**:
  - **L1 Exact Match**: Fast SHA-256 hash lookup (<1ms)
  - **L2 Semantic Match**: Local embedding + cosine similarity (<15ms), configurable threshold (default 0.92)
- ✅ **Smart Fallback Routing** — Automatic failover to secondary API keys or providers (429/5xx errors)
- ✅ **Embedded Storage** — In-memory and SQLite-vec backends (zero external dependencies)
- ✅ **Streaming SSE Support** — Fully supports `stream: true` with zero latency overhead
- ✅ **CLI & Metrics** — Live dashboard with hit rates and latency insights
- ✅ **Docker & PyPI** — Single command deployment
- ✅ **Production Ready** — 50+ tests, 80%+ coverage, strict type checking, full documentation

### Roadmap

**Phase 2: Enhanced Features**
- Distributed edge-proxy network support
- Centralized semantic cache sharing across microservices
- Smart invalidation hooks (tag-based, user-based, document-based)
- PII scrubbing before caching (regex + NER)
- Customer-managed encryption keys (CMEK)

**Phase 3: Advanced Capabilities**
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
Prospect Proxy Server (FastAPI)
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
prospect-ai/
├── .github/workflows/
│   ├── ci.yml                  # Test matrix (3.11/3.12), linting, build
│   └── publish.yml             # PyPI + Docker release
├── Dockerfile                  # Ultra-lightweight multi-stage image
├── pyproject.toml              # Build config, CLI entrypoint
├── README.md                   # This file
├── LICENSE                     # MIT license
├── CHANGELOG.md                # Release notes
├── CONTRIBUTING.md             # Contribution guide
├── SECURITY.md                 # Vulnerability reporting
├── CODE_OF_CONDUCT.md          # Community standards
├── docs/
│   ├── DEPLOYMENT.md           # Production deployment guide
│   └── adr/
│       └── 001-architecture.md # Architecture decision record
├── src/prospect_ai/
│   ├── __init__.py             # Public API
│   ├── cli.py                  # Typer CLI (`prospect-ai start`, `prospect-ai stats`)
│   ├── domain/
│   │   └── types.py            # Immutable domain models (CacheEntry, Route, etc.)
│   ├── core/
│   │   ├── similarity.py       # Cosine similarity + threshold scoring
│   │   ├── normalizer.py       # Request normalization (exact match hashing)
│   │   ├── embedder.py         # ONNX FastEmbed wrapper (M1.2)
│   │   └── router.py           # Fallback routing logic
│   └── infrastructure/
│       ├── server.py           # FastAPI routes (/v1/chat/completions)
│       ├── proxy_gateway.py    # Async HTTP + SSE streaming
│       ├── storage/
│       │   ├── base.py         # Abstract storage interface
│       │   ├── memory.py       # In-memory backend
│       │   └── sqlite_vec.py   # SQLite-vec backend
│       └── telemetry.py        # Prometheus + OpenTelemetry
└── tests/
    ├── test_semantic_cache.py              # Foundation tests (20+)
    ├── test_m1_2_integration.py            # Server L2 integration (12)
    ├── test_m1_2_e2e.py                    # E2E proxy + cache (5)
    ├── test_proxy_streaming.py             # SSE streaming (13)
    ├── test_functional_core.py             # Similarity, normalization
    └── test_benchmarks.py                  # Performance validation
```

---

## Configuration

### prospect.yaml

```yaml
# Prospect gateway configuration

server:
  port: 8000
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

## Usage Examples

### Basic Cache Monitoring

```bash
# Start proxy
prospect-ai start --port 8000 --similarity 0.90

# In another terminal, check stats
prospect-ai stats

# View cache entries
prospect-ai cache list

# Clear cache
prospect-ai cache clear
```

### Custom Similarity Threshold

```bash
# Aggressive caching (more hits, lower precision)
prospect-ai start --similarity 0.85

# Conservative (fewer hits, higher precision)
prospect-ai start --similarity 0.95
```

### With Docker Compose

```yaml
version: '3.9'
services:
  prospect:
    image: ghcr.io/craftedwithintent/prospect-ai:latest
    ports:
      - "8000:8000"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SIMILARITY_THRESHOLD: "0.92"
  
  app:
    build: .
    ports:
      - "9000:9000"
    environment:
      OPENAI_BASE_URL: "http://prospect:8000/v1"
    depends_on:
      - prospect
```

Run:
```bash
docker-compose up
```

---

## CLI Reference

```
prospect-ai [OPTIONS] COMMAND

Commands:
  start       Start the Prospect proxy gateway
  stats       Display cache performance metrics
  cache       Cache management (list, clear, export)
  config      Show or validate configuration
  health      Check health status

Options:
  --version           Show version and exit
  --help              Show this message and exit
  --config FILE       Path to config file (default: prospect.yaml)

Examples:
  prospect-ai start --port 8000 --similarity 0.92
  prospect-ai stats --format json
  prospect-ai cache list --limit 100
  prospect-ai config validate
```

### start

```
Usage: prospect-ai start [OPTIONS]

Start the Prospect AI proxy gateway.

Options:
  --port PORT                        Listening port (default: 8000)
  --host HOST                        Listening host (default: 0.0.0.0)
  --similarity THRESHOLD             L2 similarity threshold (0.0-1.0, default: 0.92)
  --workers WORKERS                  Worker threads (default: 4)
  --backend BACKEND                  Cache backend: memory, sqlite-vec (default: memory)
  --log-level LEVEL                  Logging level: debug, info, warning, error (default: info)
  --help                             Show this message and exit
```

### stats

```
Usage: prospect-ai stats [OPTIONS]

Display cache performance metrics.

Options:
  --format FORMAT                    Output format: text, json (default: text)
  --help                             Show this message and exit
```

---

## Performance Benchmarks

### Latency (P50/P99)

| Scenario | P50 Latency | P99 Latency | Notes |
|----------|------------|------------|-------|
| L1 Exact Match (hash lookup) | 0.8ms | 1.2ms | In-memory hash table |
| L2 Semantic Match (embedding + similarity) | 12ms | 18ms | ONNX model + cosine calc |
| Cache Miss → Upstream | 1,200ms | 3,500ms | Upstream latency |
| **Latency Improvement (Cache Hit)** | **99%** | **99%** | 1,200–3,500ms → <15ms |

### Cache Hit Rate

| Workload | Hit Rate | Tokens Saved | Cost Reduction |
|----------|----------|--------------|----------------|
| Conversational chatbot | 40–55% | 8–11x | 40–55% |
| FAQ-based support | 60–75% | 15–20x | 60–75% |
| Repeated queries | 80%+ | 20x+ | 80%+ |

---

## Deployment

### Local Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --cov=src/prospect_ai

# Start proxy
prospect-ai start --port 8000 --similarity 0.92
```

### Docker

```bash
# Build locally
docker build -t prospect-ai:latest .

# Run with environment variables
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  prospect-ai:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prospect-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: prospect
  template:
    metadata:
      labels:
        app: prospect
    spec:
      containers:
      - name: prospect
        image: ghcr.io/craftedwithintent/prospect-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: prospect-secrets
              key: openai-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
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

## Testing

### Run Test Suite Locally

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/prospect_ai --cov-report=term-missing

# Run only unit tests (fast)
pytest tests/test_semantic_cache.py -v

# Run specific test
pytest tests/test_m1_2_integration.py::test_l2_lookup -v
```

### Coverage Target

Minimum 80% (enforced by CI/CD)

### Add New Tests

1. Create test file in `tests/test_*.py`
2. Write test functions (pytest conventions)
3. Ensure they pass: `pytest tests/test_*.py -v`
4. Verify coverage increase: `--cov-report=term-missing`
5. Update [CHANGELOG.md](CHANGELOG.md) with your test additions
6. Commit with your changes

---

## Contributing

This is an open-source project. Contributions welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Ensure all checks pass locally:
   ```bash
   ruff check src/ tests/
   pyright src/ tests/
   pytest tests/ --cov=src/prospect_ai
   ```
6. Update [CHANGELOG.md](CHANGELOG.md) with your changes
7. Submit a PR with a clear description

### Code Style

- **Formatting:** Ruff (enforced)
- **Type Checking:** Pyright strict mode (enforced)
- **Testing:** Pytest with >80% coverage (enforced)
- **PR Size:** Max 5 files per PR (encourages focused changes)

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

**CraftedWithIntent™** — Built for precision. Built to scale.

---

**No Shared Dependencies:** Prospect is completely decoupled from other CraftedWithIntent products. It works standalone as a semantic caching reverse proxy for any LLM API.

---

## Questions? Support?

- 📖 [Documentation](../../docs/)
- 📋 [Deployment Guide](docs/DEPLOYMENT.md)
- 🏗️ [Architecture Decision Record](docs/adr/001-architecture.md)
- 🐛 [GitHub Issues](https://github.com/CraftedWithIntent/prospect-ai/issues)
- 💬 [GitHub Discussions](https://github.com/CraftedWithIntent/prospect-ai/discussions)
- 📧 [dev@crafted.ai](mailto:dev@crafted.ai)
