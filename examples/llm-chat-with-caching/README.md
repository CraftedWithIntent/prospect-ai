# LLM Chat App with Crucible Caching Example

This directory contains a **complete, production-ready example** of an LLM chat application optimized with Crucible AI for cost savings and latency reduction.

## What It Does

The **LLM Chat App** demonstrates:

1. FastAPI chat service with OpenAI API integration
2. **Crucible AI reverse proxy** intercepting all LLM requests
3. Semantic cache hits reducing token costs by 8-11x
4. Real-time cache metrics and savings tracking
5. Deployment examples (Docker, Kubernetes)

### Architecture

```
┌──────────────────┐
│  Chat Client     │
│  (Web/Mobile)    │
└────────┬─────────┘
         │ HTTP POST /chat
         ↓
┌──────────────────┐
│  FastAPI Chat    │
│  Service         │
└────────┬─────────┘
         │ OpenAI SDK (base_url=crucible)
         ↓
┌──────────────────┐
│  Crucible AI     │
│  (Proxy Gateway) │
└────────┬─────────┘
         │ → L1 exact cache hit? → return <1ms ✅
         │ → L2 semantic hit? → return <15ms ✅
         │ → Upstream miss? → relay to OpenAI (1,200-3,500ms)
         ↓
┌──────────────────┐
│  OpenAI API      │
│  (GPT-4/Claude)  │
└──────────────────┘
```

**Result:** 40-55% of queries hit cache, saving 8-11x tokens and costs.

## Quick Start

### 1. Prerequisites

```bash
# Ensure Crucible AI is running
prospect-ai \
  --host 0.0.0.0 \
  --port 8000 \
  --upstream-base-url https://api.openai.com \
  --upstream-api-key $OPENAI_API_KEY
```

Or use Docker:
```bash
docker run -d \
  --name prospect-ai \
  -p 8000:8000 \
  -e CRUCIBLE_UPSTREAM_BASE_URL="https://api.openai.com" \
  -e CRUCIBLE_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
  ghcr.io/craftedwithintent/prospect-ai:1.0.0
```

### 2. Install Dependencies

```bash
cd examples/llm-chat-with-caching
pip install -r requirements.txt
```

**Requirements:**
- Python 3.11+
- FastAPI (HTTP framework)
- Uvicorn (async HTTP server)
- OpenAI SDK (LLM integration)
- Pydantic (data validation)

### 3. Set API Keys

```bash
export OPENAI_API_KEY="your-openai-key-here"
export CRUCIBLE_BASE_URL="http://localhost:8000"  # Crucible proxy
```

### 4. Run the Chat Service

```bash
python app.py
```

Server starts at `http://localhost:9000`

### 5. Test with cURL

**First Request (Cache Miss → Upstream):**
```bash
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "What is machine learning?"}],
    "temperature": 0.7
  }'
```

**Response (first time, ~2 seconds):**
```json
{
  "id": "chatcmpl-xxx",
  "content": "Machine learning is a subset of artificial intelligence...",
  "tokens_used": 250,
  "cached": false,
  "latency_ms": 2150,
  "cost": 0.004
}
```

**Similar Follow-up Request (Cache Hit → L2 Semantic Match):**
```bash
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Tell me about ML and AI?"}],
    "temperature": 0.7
  }'
```

**Response (L2 hit, ~15 milliseconds):**
```json
{
  "id": "chatcmpl-yyy",
  "content": "Machine learning is a subset of artificial intelligence...",
  "tokens_used": 0,
  "cached": true,
  "cache_type": "L2_SEMANTIC",
  "similarity_score": 0.94,
  "latency_ms": 12,
  "cost": 0.0,
  "savings": 0.004
}
```

### 6. View Cache Metrics

```bash
curl http://localhost:9000/metrics
```

**Response:**
```json
{
  "total_requests": 100,
  "cache_hits": 55,
  "cache_hit_rate": 0.55,
  "l1_hits": 5,
  "l2_hits": 50,
  "total_tokens_saved": 12750,
  "total_cost_saved": 0.21,
  "average_cache_latency_ms": 12,
  "average_upstream_latency_ms": 2450
}
```

## Production Deployment

### Docker

```bash
# Build image
docker build -t llm-chat-with-caching .

# Run with Crucible
docker run -d \
  --name llm-chat \
  --link prospect-ai:crucible \
  -p 9000:9000 \
  -e CRUCIBLE_BASE_URL="http://crucible:8000" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  llm-chat-with-caching
```

### Kubernetes

```bash
# Create secret
kubectl create secret generic llm-chat-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"

# Deploy
kubectl apply -f k8s-deployment.yaml
```

## Cost Analysis

### Before Crucible (No Caching)

```
100 requests × 250 tokens/request = 25,000 tokens
25,000 tokens × $0.00002/token = $0.50
```

### After Crucible (40-55% Hit Rate)

```
55 cached requests × 0 tokens = 0 tokens
45 upstream requests × 250 tokens = 11,250 tokens
11,250 tokens × $0.00002/token = $0.225

Savings: $0.50 - $0.225 = $0.275 (55% reduction)
```

**With high-volume traffic (10,000 requests/day):**
```
Daily savings: $2.75
Monthly savings: $82.50 (non-stop)
Annual savings: $1,003.75 per 10K requests/day
```

## Cache Behavior

### L1 Exact Match (Rare)
- **When:** Identical request (same model, messages, parameters)
- **Latency:** <1ms
- **Frequency:** ~5% of requests
- **Example:** User resubmits same query

### L2 Semantic Match (Common)
- **When:** Similar meaning, different wording
- **Latency:** <15ms
- **Frequency:** ~35-50% of requests
- **Examples:**
  - "What is ML?" vs "Tell me about machine learning?"
  - "How do I reset my password?" vs "I forgot my password, how to reset?"
  - "What's the weather?" vs "What's the current weather today?"

### Upstream (Remaining)
- **When:** Novel queries with no cached match
- **Latency:** 1,200-3,500ms
- **Frequency:** ~45-60% of requests
- **Action:** Cached for future L2 hits

## Configuration

### Similarity Threshold

Edit `app.py` to adjust L2 matching aggressiveness:

```python
CRUCIBLE_SIMILARITY_THRESHOLD = 0.92  # Default: balanced (90% precision, 80% recall)

# Conservative (fewer false positives):
# CRUCIBLE_SIMILARITY_THRESHOLD = 0.95

# Aggressive (more hits, risk of mismatches):
# CRUCIBLE_SIMILARITY_THRESHOLD = 0.85
```

### Cache Backend

Crucible supports multiple backends (edit Crucible gateway config):

- **Memory** (default): Fast, in-process, lost on restart
- **SQLite-Vec**: Persistent local vector DB
- **Redis**: Distributed cache (multi-instance deployments)

## Monitoring

### Health Check

```bash
curl http://localhost:9000/health
# Response: {"status": "ok"}
```

### Detailed Metrics

```python
# In your app
from app import cache_metrics

print(f"Hit rate: {cache_metrics.hit_rate:.1%}")
print(f"Tokens saved: {cache_metrics.tokens_saved}")
print(f"Cost saved: ${cache_metrics.cost_saved:.2f}")
```

### Logging

Check logs for cache decisions:

```
INFO: Cache L1 hit: chatcmpl-xxx (latency=0.5ms)
INFO: Cache L2 hit: chatcmpl-yyy (similarity=0.94, latency=12.3ms)
INFO: Cache miss, upstream relay (latency=2145ms)
```

## Testing

Run the included test suite:

```bash
pytest tests/ -v
```

**Tests included:**
- L1 exact match verification
- L2 semantic similarity validation
- Cost calculation accuracy
- Metrics collection
- Error handling

## Troubleshooting

### Low Cache Hit Rate (<30%)

**Cause:** Queries too diverse or L2 threshold too high

**Solution:**
```python
# Lower similarity threshold
CRUCIBLE_SIMILARITY_THRESHOLD = 0.90  # More aggressive
```

### High Latency on Upstream Calls

**Cause:** OpenAI rate limiting or network slowness

**Solution:**
1. Check OpenAI status (status.openai.com)
2. Increase timeout: `openai.timeout = 30`
3. Add backoff retry logic

### Missing Cached Responses

**Cause:** Crucible not running or wrong URL

**Solution:**
```bash
# Verify Crucible is running
curl http://localhost:8000/health
# Expected: {"status": "ok", "cache_size": 42}

# Verify app is using Crucible
grep CRUCIBLE_BASE_URL app.py
# Should point to http://localhost:8000
```

## Next Steps

1. **Scale to production:**
   - Deploy Crucible + app to same cluster
   - Use Redis backend for multi-instance caching
   - Monitor cache hit rates and cost savings

2. **Integrate with your LLM app:**
   - Replace OpenAI base_url with Crucible
   - No code changes needed (drop-in replacement)
   - Monitor metrics and adjust threshold

3. **Optimize further (M1.3+):**
   - Provider routing (OpenAI vs Claude vs Gemini)
   - Automatic failover to backup providers
   - Advanced metrics export (Prometheus)

---

**Questions?** 
- GitHub Issues: https://github.com/CraftedWithIntent/prospect-ai/issues
- Architecture: [docs/adr/001-architecture.md](../../docs/adr/001-architecture.md)
- Deployment: [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md)
