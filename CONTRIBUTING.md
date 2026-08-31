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

### Submitting PR

1. **Push to origin:** `git push origin feature/M1.X-description`
2. **Create PR:** `gh pr create --title "feat(M1.X): ..." --body "..."`
3. **Wait for CI:** All checks must pass (ruff, pytest, type checking)
4. **Address feedback:** Push fixes to same branch (auto-updates PR)
5. **Merge:** Squash merge:
   ```bash
   gh pr merge <PR_NUMBER> --squash
   ```
6. **Delete branch** after merge:
   ```bash
   git branch -d feature/M1.X-description
   git push origin --delete feature/M1.X-description
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
   twine upload dist/prospect-ai-1.1.0-py3-none-any.whl
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
