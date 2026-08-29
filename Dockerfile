# Multi-stage Dockerfile for ultra-lightweight Crucible proxy

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY pyproject.toml .
COPY src ./src
COPY README.md .

# Build wheel
RUN pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .


FROM python:3.11-slim

WORKDIR /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install runtime dependencies
RUN pip install --no-cache-dir --no-index --find-links /wheels crucible-proxy && \
    rm -rf /wheels

# Expose default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run Crucible
ENTRYPOINT ["crucible"]
CMD ["start", "--port", "8080"]
