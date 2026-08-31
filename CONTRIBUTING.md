# Contributing to Prospect AI

Thank you for contributing! This guide explains how to develop, test, and submit changes to Prospect AI.

## Setup

### Clone and install in dev mode

```bash
git clone https://github.com/CraftedWithIntent/prospect-ai.git
cd prospect-ai
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -e .[dev]
```

### Verify setup

```bash
pytest tests/ -v
python -m py_compile src/prospect_ai/**/*.py
```

## Architecture

Prospect AI follows **Functional Core + Imperative Shell** (ADR-001):

- **Functional Core**: Pure similarity scoring (cosine similarity, embeddings, normalization, routing)
- **Imperative Shell**: FastAPI gateway (async HTTP relay), storage backends (in-memory, SQLite, Redis)

### Code Organization

```
src/prospect_ai/
├── core/                 # M1.2–M1.3: Pure functions
│   ├── embedder.py      # ONNX FastEmbed wrapper (M1.2)
│   ├── similarity.py    # Cosine similarity, scoring (M1.2)
│   ├── normalizer.py    # Payload normalization (M1.0)
│   └── router.py        # Provider routing logic (M1.3)
├── domain/              # Shared types (cache entry, similarity score)
│   └── types.py         # Pydantic models (immutable)
├── infrastructure/      # M1.1: Imperative layer
│   ├── server.py        # FastAPI gateway (OpenAI-compatible)
│   ├── proxy_gateway.py # Async upstream relay
│   └── storage/         # Pluggable backends
│       ├── base.py      # CacheStorageBackend abstract
│       ├── memory.py    # In-memory + L2 search
│       ├── sqlite_vec.py # SQLite-Vec (deterministic)
│       └── redis.py     # Redis (distributed)
└── cli.py              # M1.3+: CLI entrypoint

tests/
├── test_functional_core.py         # Core logic (similarity, routing)
├── test_semantic_cache.py          # L2 search, embedding quality
├── test_m1_2_integration.py        # Server L2 integration
├── test_m1_2_e2e.py                # End-to-end (upstream → cache)
└── test_proxy_streaming.py         # Async HTTP relay
```

## Code Style

### Linting & Formatting

Prospect AI uses **Ruff** for all style enforcement:

```bash
ruff check src tests         # Check only
ruff check --fix src tests   # Auto-fix
```

### Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
extend-ignore = [
  "BLE001",  # Blind exception catches (Phase 1: CLI error propagation)
]
```

### Type Hints

- All functions must have parameter + return type hints
- Use `from typing import ...` for generic types
- Frozen Pydantic models for immutability: `model_config = ConfigDict(frozen=True)`
- Use strict `pyright` mode (no `Any` without explicit ignore)

### Imports

- Group: stdlib, third-party, local (in that order)
- Alphabetical within each group
- Ruff auto-sorts on `--fix`

### Docstrings

- Use triple-quoted docstrings for all public functions, classes, modules
- Format: Google-style (Args, Returns, Raises, Example)
- Required for: CLI commands, caching logic, storage backends, public APIs

## Testing

### Run tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_semantic_cache.py -v

# With coverage
pytest tests/ --cov=src/prospect_ai --cov-report=term-missing
```

### Coverage Requirements

- Minimum: **80%**
- Target: **90%+**
- Enforced by CI/CD

### Writing Tests

**Test file naming:** `test_<module>.py`

**Mocking external services:**
```python
from unittest.mock import patch, MagicMock
import pytest

@patch("prospect_ai.infrastructure.proxy_gateway.httpx.AsyncClient")
def test_proxy_cache_miss(mock_client):
    mock_client.return_value.post.return_value = MagicMock(status_code=200)
    # Test assertion
```

**Fixtures:**
```python
@pytest.fixture
def sample_cache_entry():
    from prospect_ai.domain.types import CacheEntry
    return CacheEntry(
        query="What is AI?",
        response='{"result": "Artificial Intelligence"}',
        hash="abc123"
    )
```

### Adding Cache Storage Backends

1. **Create backend class** extending `CacheStorageBackend` in `src/prospect_ai/infrastructure/storage/<name>.py`:
   ```python
   from prospect_ai.infrastructure.storage.base import CacheStorageBackend
   
   class MyBackend(CacheStorageBackend):
       """Custom cache storage backend."""
       async def get(self, key: str) -> Optional[str]:
           # Retrieve cached response
           return cached_response
       
       async def set(self, key: str, value: str) -> None:
           # Store response in cache
           pass
   ```

2. **Add tests** in `tests/test_<name>.py`:
   ```python
   @pytest.mark.asyncio
   async def test_backend_get():
       backend = MyBackend()
       await backend.set("key", "value")
       result = await backend.get("key")
       assert result == "value"
   ```

3. **Update docs**:
   - Add to README.md storage backends section
   - Document configuration options
   - Add deployment guide for your backend

## Examples

Prospect AI examples live in `examples/` and demonstrate **complete, production-ready LLM caching systems**.

### Why Examples Matter

Examples are the best way for users to:
- ✅ Learn how to integrate Prospect AI
- ✅ See semantic caching in action
- ✅ Copy-paste working code
- ✅ Understand performance benefits
- ✅ Deploy to production

### Example Structure

Each example follows this structure:

```
examples/
├── README.md                          # Index of all examples
│
└── YOUR-CACHE-SYSTEM/
    ├── README.md                      # Setup, API reference, troubleshooting
    ├── app.py                         # Full LLM app with caching (production-ready)
    ├── requirements.txt               # Dependencies
    ├── Dockerfile                     # Production image
    └── tests/
        └── test_app.py                # 10+ integration tests
```

### Adding a New Example

**Step 1: Create directory structure**

```bash
mkdir -p examples/YOUR-CACHE-SYSTEM/tests
```

**Step 2: Implement LLM app with Prospect AI (`app.py`)**

Requirements:
- ✅ Use FastAPI or another HTTP framework
- ✅ Integrate Prospect AI as reverse proxy or direct library
- ✅ Include LLM integration (Claude, GPT-4, Bedrock, etc.)
- ✅ Use Pydantic for request/response validation
- ✅ Include comprehensive docstrings
- ✅ Handle errors gracefully
- ✅ Log cache metrics (hit rate, tokens saved)
- ✅ Runnable with `python app.py` (no CLI args)
- ✅ ~250-350 lines including comments

Example template:

```python
"""LLM Chat Service with Prospect AI Caching."""

import logging
from fastapi import FastAPI
from pydantic import BaseModel
import prospect_cache_ai

app = FastAPI(title="LLM Chat with Caching")
logger = logging.getLogger(__name__)

# Initialize Prospect AI cache
cache = prospect_cache_ai.CacheClient(backend="memory")

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    model: str = "claude-3-sonnet"

class ChatResponse(BaseModel):
    """Chat response model."""
    reply: str
    cached: bool
    tokens_saved: int

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process chat request with semantic caching."""
    # Check cache
    cached_response = await cache.get_semantic(request.message)
    
    if cached_response:
        return ChatResponse(
            reply=cached_response["text"],
            cached=True,
            tokens_saved=cached_response["tokens"]
        )
    
    # Call LLM
    response = call_llm(request.message, model=request.model)
    
    # Cache response
    await cache.set(
        query=request.message,
        response=response["text"],
        tokens=response["tokens"]
    )
    
    return ChatResponse(
        reply=response["text"],
        cached=False,
        tokens_saved=0
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 3: Create test suite (`tests/test_app.py`)**

Requirements:
- ✅ 10+ test cases
- ✅ Happy path (successful chat)
- ✅ Cache hits (same query, similar query)
- ✅ Cache misses (new query)
- ✅ Error handling (LLM errors, network errors)
- ✅ Performance (latency benchmarks)
- ✅ Metrics (cache hit rate, token savings)

Example test:

```python
import pytest
from fastapi.testclient import TestClient
from app import app, cache

client = TestClient(app)

@pytest.mark.asyncio
async def test_cache_hit():
    """Test semantic cache hit."""
    # First request (cache miss)
    response1 = client.post("/chat", json={"message": "What is AI?"})
    assert response1.status_code == 200
    assert response1.json()["cached"] is False
    
    # Second request (cache hit - similar query)
    response2 = client.post("/chat", json={"message": "Tell me about AI"})
    assert response2.status_code == 200
    assert response2.json()["cached"] is True
    assert response2.json()["tokens_saved"] > 0
```

**Step 4: Create `requirements.txt`**

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
prospect-cache-ai==1.0.0
anthropic==0.7.1
requests==2.31.0
```

**Step 5: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000
CMD ["python", "app.py"]
```

**Step 6: Create detailed `README.md`**

Must include:

- 📝 **What It Does** — 1-2 paragraphs explaining the system
- 🏗️ **Architecture** — Diagram or text description
- 🚀 **Quick Start** — Install, run, test (5 steps max)
- 📡 **API Reference** — Request/response models with examples
- 💰 **Cost Analysis** — Cache savings calculation
- 🧪 **Test Suite Overview** — What each test case covers
- 🔧 **Troubleshooting** — Common errors and solutions
- ➡️ **Next Steps** — How to extend or modify the example

See [examples/llm-chat-with-caching/README.md](examples/llm-chat-with-caching/README.md) for a complete template.

**Step 7: Test locally**

```bash
cd examples/YOUR-CACHE-SYSTEM

# Install deps
pip install -r requirements.txt

# Run app
python app.py

# In another terminal, run tests
pytest tests/ -v

# All tests should pass ✅
```

**Step 8: Update examples index**

Edit [examples/README.md](examples/README.md) to add your example in the "Quick Links" section:

```markdown
### Your Cache System Name

**Directory:** `your-cache-system/`

Brief description of what it does.

**Quick Start:**
```bash
cd your-cache-system
pip install -r requirements.txt
python app.py
pytest tests/ -v
```
```

**Step 9: Submit PR**

```bash
git add examples/YOUR-CACHE-SYSTEM/
git add examples/README.md
git commit -m "feat: Add YOUR-CACHE-SYSTEM example"
gh pr create --title "feat: Add YOUR-CACHE-SYSTEM example"
```

### Example Quality Checklist

Before submitting an example, verify:

- [ ] `app.py` is complete and production-ready (no TODOs)
- [ ] `app.py` uses LLM (Claude, GPT-4, Bedrock, etc.)
- [ ] `app.py` integrates Prospect AI for caching
- [ ] `app.py` has comprehensive docstrings
- [ ] `app.py` handles errors and logs properly
- [ ] `app.py` tracks cache metrics (hit rate, cost savings)
- [ ] `requirements.txt` lists all dependencies with pinned versions
- [ ] `tests/test_app.py` has 10+ test cases
- [ ] Test cases cover happy path, cache hits, misses, errors, performance
- [ ] `Dockerfile` is production-ready
- [ ] `README.md` has all required sections
- [ ] `README.md` includes working Quick Start instructions
- [ ] API reference shows all request/response fields
- [ ] All tests pass when running locally
- [ ] App runs with `python app.py` (no CLI args)
- [ ] Example is realistic and solves a real problem
- [ ] Code follows Ruff style guidelines (`ruff check --fix`)
- [ ] Example is added to [examples/README.md](examples/README.md)

### Example Ideas

Looking for example ideas? Consider:

- **Chat Service** — FastAPI chat with semantic caching + cost tracking
- **Document QA** — Answer questions about documents with cache optimization
- **Code Generation** — Generate code faster with cached common patterns
- **Content Translation** — Translate content with cache for common phrases
- **Research Assistant** — Research tool with cached knowledge base
- **Customer Support** — Support bot with cached response patterns
- **Data Analysis** — Analyze data with cached computation results
- **Image Captioning** — Generate captions with cached image interpretations

### During Development

- Keep scope small: **Max 5 files per PR** (excludes lockfiles, generated files)
- Build frequently: `pytest tests/ --cov=src/prospect_ai`
- Run tests: `pytest tests/ -v --cov`
- Update CHANGELOG.md with your changes

### Submitting PR

1. **Commit message format:**
   ```
   feat: Brief description (M1.X: Component if applicable)

   Longer explanation of what changed and why.
   Include test coverage summary.
   Fixes #ISSUE_NUMBER.
   ```

2. **Create PR via CLI:**
   ```bash
   git push origin feature/ISSUE-description
   gh pr create --title "feat: M1.X: Brief description" \
     --body "Detailed description, testing notes, architecture decisions"
   ```

3. **Wait for CI:** All checks must pass (ruff, pytest, type checking)

4. **Address feedback:** Push fixes to same branch (auto-updates PR)

5. **Merge:** Author squashes + merges (never fast-forward)
   ```bash
   gh pr merge <PR_NUMBER> --squash
   ```

6. **Delete branch** after merge:
   ```bash
   git branch -d feature/ISSUE-description
   git push origin --delete feature/ISSUE-description
   ```

## PR Workflow

### Before You Start

1. **Check for open PRs:** `gh pr list --state open`
2. **Verify main clean:** `git log main --oneline | head -1`
3. **Search codebase** for existing implementations (zero duplication policy):
   ```bash
   rg "def .*cache" src/prospect_ai/
   find src/prospect_ai -name "*.py" -exec grep -l "class.*Backend" {} +
   ```
4. **Update issue label:** `status:backlog` → `status:in-progress` (if applicable)
5. **Create feature branch:** `git checkout -b feature/M1.X-description`

### Commit Message Format

```
feat(M1.X): Brief description

Longer explanation of what changed and why.
Include architecture decisions.
Fixes #ISSUE_NUMBER.
```

## Release Process

### Version Bumping

Prospect AI uses semantic versioning: **MAJOR.MINOR.PATCH**

- **MAJOR:** Breaking API changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes

### Release Checklist

1. **Update version** in `pyproject.toml`:
   ```toml
   [project]
   version = "1.1.0"
   ```

2. **Update CHANGELOG.md** with release notes

3. **Tag commit:**
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

4. **Build and publish to PyPI:**
   ```bash
   pip install build twine
   python -m build
   twine upload dist/prospect-cache-ai-1.1.0-py3-none-any.whl
   ```

## Troubleshooting

### "ImportError: No module named 'prospect_ai'"

**Cause:** Virtual environment not activated or package not installed in dev mode

**Fix:** 
```bash
source venv/bin/activate
pip install -e .[dev]
```

### "ruff: BLE001 Do not catch blind exception"

**Rationale:** Phase 1 design uses broad exception handlers for CLI error propagation. Suppressed in config.

**If adding new exception handler:** Document why in code comment.

### Test failures with "ONNX model not found"

**Cause:** FastEmbed model download failed (network issue)

**Fix:**
```bash
# Manually download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Re-run tests
pytest tests/ -v
```

## Questions?

- Open a GitHub Issue: [Issues](https://github.com/CraftedWithIntent/prospect-ai/issues)
- Start a Discussion: [Discussions](https://github.com/CraftedWithIntent/prospect-ai/discussions)
- Review architecture: [docs/adr/001-architecture.md](docs/adr/001-architecture.md)

---

**Thank you for making Prospect AI better!**
