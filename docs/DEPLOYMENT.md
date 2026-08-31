# Deployment Guide

This guide covers deploying Crucible AI in production environments.

## Quick Start (Local)

```bash
# Install
pip install crucible-ai

# Run gateway
crucible-ai --host 0.0.0.0 --port 8000 --upstream-base-url https://api.openai.com --upstream-api-key $OPENAI_API_KEY

# Test
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Docker Deployment

### Build Image

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir crucible-ai

# Expose gateway port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Run gateway
CMD ["crucible-ai", "--host", "0.0.0.0", "--port", "8000"]
```

### Run Container

```bash
docker run -d \
  --name crucible-ai \
  --port 8000:8000 \
  -e CRUCIBLE_UPSTREAM_BASE_URL="https://api.openai.com" \
  -e CRUCIBLE_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
  -e CRUCIBLE_CACHE_BACKEND="memory" \
  crucible-ai:latest
```

## Kubernetes Deployment

### ConfigMap (Configuration)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: crucible-config
namespace: default
data:
  CRUCIBLE_HOST: "0.0.0.0"
  CRUCIBLE_PORT: "8000"
  CRUCIBLE_CACHE_BACKEND: "memory"
  CRUCIBLE_SIMILARITY_THRESHOLD: "0.92"
```

### Secret (API Keys)

```bash
kubectl create secret generic crucible-secrets \
  --from-literal=CRUCIBLE_UPSTREAM_API_KEY=$OPENAI_API_KEY \
  --from-literal=CRUCIBLE_UPSTREAM_BASE_URL="https://api.openai.com"
```

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-ai
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crucible-ai
  template:
    metadata:
      labels:
        app: crucible-ai
    spec:
      containers:
      - name: crucible-ai
        image: ghcr.io/craftedwithintent/crucible-ai:1.0.0
        ports:
        - containerPort: 8000
          name: http

        envFrom:
        - configMapRef:
            name: crucible-config
        - secretRef:
            name: crucible-secrets

        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2

        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: crucible-ai
  namespace: default
spec:
  selector:
    app: crucible-ai
  type: ClusterIP
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
    name: http
```

### Deploy

```bash
kubectl apply -f config.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml

# Verify
kubectl get pods -l app=crucible-ai
kubectl logs deployment/crucible-ai -f
```

## Reverse Proxy Setup (Nginx)

### Configuration

```nginx
upstream crucible_backend {
    server crucible-ai:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Cache headers
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=crucible:10m max_size=1g;

    location /v1/chat/completions {
        proxy_pass http://crucible_backend;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;

        # Streaming
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_request_buffering off;

        # Authentication (optional)
        # auth_request /auth;
    }

    location /health {
        proxy_pass http://crucible_backend;
        access_log off;
    }
}
```

## Environment Variables

```bash
# Gateway
CRUCIBLE_HOST="0.0.0.0"                          # Listen address
CRUCIBLE_PORT="8000"                             # Listen port
CRUCIBLE_LOG_LEVEL="INFO"                        # Log level

# Upstream
CRUCIBLE_UPSTREAM_BASE_URL="https://api.openai.com"  # Upstream provider
CRUCIBLE_UPSTREAM_API_KEY="sk-..."               # API key (required)

# Cache
CRUCIBLE_CACHE_BACKEND="memory"                  # memory|sqlite|redis
CRUCIBLE_SIMILARITY_THRESHOLD="0.92"             # L2 threshold [0.0, 1.0]
CRUCIBLE_CACHE_MAX_SIZE="1000"                   # Max cache entries

# For Redis backend
CRUCIBLE_REDIS_URL="redis://localhost:6379"     # Redis connection

# For SQLite backend
CRUCIBLE_SQLITE_PATH="/data/cache.db"            # Database path
```

## Monitoring

### Health Check Endpoint

```bash
curl http://localhost:8000/health
# Response: {"status": "ok", "cache_size": 42}
```

### Metrics Export (Future)

```bash
curl http://localhost:8000/metrics
# Prometheus format:
# crucible_cache_hits_total{backend="memory"} 1234
# crucible_cache_misses_total{backend="memory"} 567
# crucible_upstream_latency_seconds_bucket{le="0.5"} 89
```

### Logging

```json
{
  "timestamp": "2026-09-01T01:30:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "message": "L2 cache hit",
  "model": "gpt-4",
  "cache_result": "L2_HIT",
  "similarity_score": 0.94,
  "latency_ms": 12
}
```

## Performance Tuning

### L2 Similarity Threshold

- **0.95+**: Conservative (high precision, low recall)
  - Fewer false positives
  - More upstream calls
  - Use: When accuracy > cost savings

- **0.92** (default): Balanced
  - ~90% precision, ~80% recall
  - Good token savings
  - Best for most workloads

- **0.85-0.89**: Aggressive (low precision, high recall)
  - Highest cache hit rate
  - Risk of incorrect responses
  - Use: Low-risk queries only

### Cache Size Limits

```bash
CRUCIBLE_CACHE_MAX_SIZE=10000     # 10K entries (reasonable for 1 instance)
```

- Each entry: ~1KB (request) + 2KB (response) + ~500B (embedding) ≈ 3.5KB
- 10,000 entries ≈ 35MB RAM

For distributed deployments, use Redis backend (no size limit).

## Security Checklist

- [ ] Use TLS/HTTPS in production (no plaintext)
- [ ] Deploy behind authentication layer (OAuth2, API keys)
- [ ] Restrict network access to internal subnets only
- [ ] Rotate upstream API keys regularly
- [ ] Monitor cache for sensitive data leakage
- [ ] Enable audit logging (all requests)
- [ ] Use strong passwords for Redis (if used)
- [ ] Run container as non-root user
- [ ] Keep dependencies updated (`pip install --upgrade crucible-ai`)

## Troubleshooting

### High Latency on Upstream Calls

**Symptom:** Cache misses are slow (>5 seconds)

**Cause:** Upstream provider rate limiting or network latency

**Solution:**
1. Check upstream status (OpenAI status page)
2. Reduce concurrent requests (`max_workers` in config)
3. Increase timeout values in reverse proxy

### Low Cache Hit Rate

**Symptom:** Cache hits <20%

**Causes:**
- L2 threshold too high (0.95+)
- Queries are too diverse
- Cache too small (evicting old entries)

**Solution:**
1. Lower L2 threshold to 0.90
2. Increase cache size (`CRUCIBLE_CACHE_MAX_SIZE`)
3. Enable distributed caching (Redis)

### Memory Leak

**Symptom:** Memory usage growing over time

**Cause:** Unbounded cache growth

**Solution:**
1. Set `CRUCIBLE_CACHE_MAX_SIZE` (default: 1000)
2. Switch to Redis backend (memory on server, not in process)
3. Restart process weekly (systemd timer)

---

**Need help?** Open an issue: https://github.com/CraftedWithIntent/crucible-ai/issues
