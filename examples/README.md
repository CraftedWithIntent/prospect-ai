# Prospect AI Examples

Complete, production-ready examples demonstrating Prospect AI semantic caching in real-world scenarios.

## Examples

### 1. LLM Chat with Caching

**Directory:** `llm-chat-with-caching/`

A FastAPI chat service that uses Prospect AI as a reverse proxy to reduce LLM costs by 8-11x.

**Features:**
- Full chat conversation support
- Real-time cache metrics (hit rate, cost savings)
- Semantic cache demonstration (L2 hits)
- Production-ready code + tests
- Docker deployment included

**Quick Start:**
```bash
# Terminal 1: Start Prospect proxy
prospect-ai --host 0.0.0.0 --port 8000 \
  --upstream-base-url https://api.openai.com \
  --upstream-api-key $OPENAI_API_KEY

# Terminal 2: Start chat app
cd examples/llm-chat-with-caching
pip install -r requirements.txt
python app.py

# Terminal 3: Test
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "What is machine learning?"}]
  }'
```

**Expected Output (First Request):**
```json
{
  "id": "chatcmpl-xxx",
  "content": "Machine learning is a subset...",
  "tokens_used": 250,
  "cached": false,
  "latency_ms": 2150,
  "cost": 0.005
}
```

**Expected Output (Similar Follow-Up, L2 Hit):**
```json
{
  "id": "chatcmpl-yyy",
  "content": "Machine learning is a subset...",
  "tokens_used": 0,
  "cached": true,
  "cache_type": "L2_SEMANTIC",
  "similarity_score": 0.94,
  "latency_ms": 12,
  "cost": 0.0,
  "savings": 0.005
}
```

**See full README:** `llm-chat-with-caching/README.md`

---

## Key Concepts Demonstrated

### 1. Semantic Caching
- L1 exact match (rare, <1ms)
- L2 semantic match (common, <15ms)
- Graceful fallback to upstream (1,200–3,500ms)

### 2. Cost Optimization
- 40-55% of queries hit cache
- 8-11x token savings
- Real-time cost tracking

### 3. Production Patterns
- FastAPI integration
- OpenAI SDK drop-in compatibility
- Docker containerization
- Kubernetes deployment
- Comprehensive testing

### 4. Monitoring
- Cache hit rates
- Latency percentiles
- Cost savings tracking
- Error handling

---

## How Prospect Works

```
User Request
    ↓
Prospect Proxy (reverse proxy)
    ├─ L1: SHA-256 exact match → Hit (↓ <1ms)
    ├─ L2: Embedding similarity → Hit (↓ <15ms)
    └─ Miss → Forward to OpenAI (↓ 1,200-3,500ms)
    ↓
Cache Response (with embedding)
    ↓
Back to User App (fast!)
```

---

## Testing

Each example includes a comprehensive test suite:

```bash
cd llm-chat-with-caching
pip install pytest
pytest tests/ -v
```

---

## Production Deployment

### Docker

```bash
# Build chat app image
docker build -t llm-chat-app examples/llm-chat-with-caching/.

# Run with Prospect
docker-compose up
```

### Kubernetes

```bash
# See examples/llm-chat-with-caching/k8s-deployment.yaml
kubectl apply -f examples/llm-chat-with-caching/k8s-deployment.yaml
```

---

## Cost Savings Calculator

### Example: 10,000 requests/day

**Without Prospect:**
```
10,000 requests × 250 tokens/request = 2.5M tokens
2.5M tokens × $0.00002/token = $50/day
= $1,500/month
```

**With Prospect (50% hit rate):**
```
5,000 cached requests × 0 tokens = 0 tokens
5,000 upstream requests × 250 tokens = 1.25M tokens
1.25M tokens × $0.00002/token = $25/day
= $750/month

Savings: $750/month (50% reduction)
```

---

## Contributing

Have a great example? Open a PR at https://github.com/CraftedWithIntent/prospect-ai/pulls

---

## More Information

- **Architecture:** [../../docs/adr/001-architecture.md](../../docs/adr/001-architecture.md)
- **Deployment Guide:** [../../docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md)
- **GitHub:** https://github.com/CraftedWithIntent/prospect-ai
