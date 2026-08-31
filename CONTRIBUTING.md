# Contributing to Crucible AI

Thank you for contributing! This guide explains how to develop, test, and submit changes to Crucible AI.

## Setup

### Clone and install in dev mode

```bash
git clone https://github.com/CraftedWithIntent/crucible-ai.git
cd crucible-ai
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -e .[dev]
```

### Verify setup

```bash
pytest tests/ -v
python -m py_compile src/crucible_ai/**/*.py
```

## Architecture

Crucible AI follows **Functional Core + Imperative Shell** (ADR-001):

- **Functional Core**: Pure similarity scoring (cosine similarity, embeddings, normalization, routing)
- **Imperative Shell**: FastAPI gateway (async HTTP relay), storage backends (in-memory, SQLite, Redis)

### Code Organization

```
src/crucible_ai/
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

Crucible AI uses **Ruff** for all style enforcement:

```bash
ruff check src tests         # Check only
ruff check --fix src tests   # Auto-fix
```

### Type Hints

- All functions must have parameter + return type hints
- Use strict `pyright` mode (no `Any` without explicit ignore)
- Frozen Pydantic models for immutability: `model_config = ConfigDict(frozen=True)`

## Testing

### Run tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_semantic_cache.py -v

# With coverage
pytest tests/ --cov=src/crucible_ai --cov-report=term-missing
```

### Coverage Requirements

- Minimum: **80%**
- Target: **90%+**
- Enforced by CI/CD

## PR Workflow

### Before You Start

1. **Check for open PRs:** `gh pr list --state open`
2. **Verify main clean:** `git log main --oneline | head -1`
3. **Search codebase** for existing implementations (zero duplication policy)
4. **Update issue label:** `status:backlog` → `status:in-progress`
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
3. **Wait for CI:** All checks must pass
4. **Merge:** Squash merge
5. **Delete branch**

## Questions?

- Open a GitHub Issue: [Issues](https://github.com/CraftedWithIntent/crucible-ai/issues)
- Review architecture: [docs/adr/001-architecture.md](docs/adr/001-architecture.md)

---

**Thank you for making Crucible AI better!**
