# WORKFLOW.md - How to Prompt Ash for Work on Crucible

This document defines how to direct work on Crucible (semantic cache & reverse proxy for LLM inference) and what to expect from execution.

**tl;dr:** Specify project context (implicit or explicit) → pick an issue → I handle the rest (branch → code → test → PR → review).

---

## Project Context: Crucible

**Workspace:** `/Users/philipthomas/.openclaw/workspaces/crucible`  
**Repository:** `https://github.com/CraftedWithIntent/crucible`  
**Tech Stack:** Python 3.11+, FastAPI, Pydantic, uv, pytest  
**Scope:** MVP phase 1 (semantic cache + reverse proxy, 3–4 weeks solo coding)

Crucible is **totally independent** of Assay, flow-ledger, game-dev, and orchestrators. It has its own GitHub repo, CI/CD, and domain logic.

---

## Directing Work on Crucible

### Standard Prompt (Explicit Project)

```
Work on crucible M2.1

or

Start crucible issue #3

or

Finish crucible M2.5 and close it
```

### Standard Prompt (Implicit, When in Crucible Session)

```
Work on M2.1

or

Start issue #3
```

(Assumes current session is Crucible; I resolve to crucible workspace automatically)

**What I do:**
1. Route to `/Users/philipthomas/.openclaw/workspaces/crucible/`
2. Read issue fully (title, body, acceptance criteria, labels)
3. Check for blockers (open PRs, broken main, upstream dependencies)
4. Create feature branch: `feature/M{X}.{Y}-{description}`
5. Execute work (code + tests per Phase 1 scope)
6. Create PR with semantic commit message
7. Update issue label: `status:backlog` → `status:in-progress` → `status:review`
8. Wait for your approval/merge

---

## Crucible-Specific Execution Discipline

### Pre-Work Checklist (MANDATORY)

Before I write any code on Crucible:

1. ✅ **Navigate to Crucible workspace** — `cd ~/.openclaw/workspaces/crucible/`
2. ✅ **Check for open PRs** — `gh pr list --state open` must be empty
3. ✅ **Verify main branch clean** — No pending merges or conflicts
4. ✅ **Codebase Reconnaissance** — Search for existing:
   - Domain types (CacheEntry, SimilarityScore, etc.)
   - Core logic (similarity.py, normalizer.py, router.py)
   - Storage backends (memory.py, sqlite_vec.py, etc.)
5. ✅ **Run local validation suite**:
   ```bash
   uv pip install -e ".[dev]"
   ruff check src tests
   pyright src
   pytest tests --cov=src/crucible
   python -m build
   ```
   All must pass (0 errors, 0 warnings).
6. ✅ **Update issue label** — `status:backlog` → `status:in-progress`
7. ✅ **Create feature branch** — `git checkout -b feature/M{X}.{Y}-{description}`
8. ✅ Only THEN start coding

### Branch Strategy

```
main (production-ready, always green)
  ↑
feature/M2.1-openai-gateway
  ↑
(local development)
  ↓
PR #N (code review)
  ↓
Merged to main via squash/rebase
```

Never commit directly to main. All work is feature-branch + PR.

### Code Quality Gates

**Linting:**
```bash
ruff check src tests
```
Must pass with 0 violations.

**Type Checking:**
```bash
pyright src
```
Strict mode, 0 errors.

**Tests:**
```bash
pytest tests --cov=src/crucible
```
- All tests passing
- Coverage ≥ 80%
- Test structure: `test_functional_core.py`, `test_proxy_streaming.py`, `test_benchmarks.py`

**Build:**
```bash
python -m build
```
Produces clean wheel + sdist.

### Commit Discipline

```
feat(core): implement cosine similarity scorer
fix(storage): handle concurrent cache writes
docs(readme): add performance benchmarks
test(normalizer): add edge case tests
```

One logical change per commit. Semantic messages per Conventional Commits.

### PR Requirements

**Title Format:**
```
M2.1: OpenAI-Compatible Gateway (Drop-in Proxy)
```

**Body Template:**
```
## Description
Implements `/v1/chat/completions` endpoint with request normalization and L1/L2 cache routing.

## Changes
- Added server.py (FastAPI routes)
- Added proxy_gateway.py (async httpx streaming)
- Updated domain/types.py with CachedResponse

## Testing
- test_proxy_streaming.py: SSE chunk reconstruction
- test_similarity_core.py: Cosine similarity edge cases
- Manual latency benchmark: <15ms L2 hit

## Related Issue
Closes #3

## Notes
Phase 1: No exception handlers in evaluators (deferred per architecture doc).
```

---

## Crucible Phase 1 Issue Breakdown

### M2.1: OpenAI-Compatible Gateway
- Expose `/v1/chat/completions` compatible with OpenAI SDK
- Handle both streaming & non-streaming requests
- Accept OPENAI_BASE_URL override
- **Files:** `src/crucible/infrastructure/server.py`, `src/crucible/infrastructure/proxy_gateway.py`

### M2.2: Hybrid Two-Tier Cache (L1 Exact + L2 Semantic)
- L1: SHA-256 hash lookup (< 1ms)
- L2: Local embedding generation + cosine similarity (< 15ms)
- Configurable threshold (default 0.92)
- **Files:** `src/crucible/core/similarity.py`, `src/crucible/core/normalizer.py`

### M2.3: Request Normalization & Caching
- Strip system prompts, canonicalize JSON
- Produce deterministic SHA-256 keys
- Handle message edge cases
- **Files:** `src/crucible/core/normalizer.py`, `tests/test_normalizer.py`

### M2.4: Local Embedding Generation (ONNX)
- Use FastEmbed / all-MiniLM-L6-v2 for in-process embeddings
- Sub-15ms latency per request
- **Files:** `src/crucible/infrastructure/embeddings.py`

### M2.5: Storage Backends (In-Memory + SQLite-vec)
- Abstract storage interface
- Memory backend (Phase 1 MVP)
- SQLite-vec backend (persistent, MVP+)
- **Files:** `src/crucible/infrastructure/storage/base.py`, `memory.py`, `sqlite_vec.py`

### M2.6: Smart Fallback Routing
- Detect 429 / 5xx from primary provider
- Failover to secondary API key or provider (Anthropic, Azure, Bedrock)
- Prioritize routes
- **Files:** `src/crucible/core/router.py`, `src/crucible/infrastructure/proxy_gateway.py`

### M2.7: CLI & Metrics Dashboard
- `crucible start --port 8080 --similarity 0.92`
- Live terminal output: hit rate, tokens saved, cost delta
- Prometheus metrics export
- **Files:** `src/crucible/cli.py`, `src/crucible/infrastructure/telemetry.py`

### M2.8: Docker & Deployment Artifacts
- Multi-stage Dockerfile (slim image, <200MB)
- GitHub Action for GHCR + Docker Hub publish
- Kubernetes manifests (optional starter template)
- **Files:** `Dockerfile`, `.github/workflows/publish.yml`

---

## Expected Outcomes Per Issue

### Features (M2.1–M2.7)

**You'll get:**
- Feature branch with passing tests
- PR with implementation + tests + updated architecture docs
- Clean git history (rebase, no merge commits)
- Exit criteria met (acceptance criteria from issue checked off)

**Success Criteria:**
- All tests passing (`pytest --cov=src/crucible`)
- Ruff + pyright clean (0 violations)
- Performance benchmark met (e.g., L2 hit < 15ms)
- Code merged to main

### Deployment (M2.8)

**You'll get:**
- Docker image built and pushed to GHCR
- PyPI package published
- GitHub release with binary artifacts
- CI workflow green on all Python versions (3.11, 3.12)

---

## Communication & Progress Updates

### During Work

If I finish in one session:
```
✅ crucible M2.3 complete. PR ready: #5
Status: Request normalization + cache key generation done.
Latency benchmark: <1ms on hash lookups, tests at 99.2% coverage.
```

If work spans multiple sessions:
```
🌿 Working on crucible M2.2 (Two-Tier Cache). 
Status: L1 exact match done, L2 semantic similarity 70% complete. 
Blocker: None. 
ETA: Next session (4 hours more).
```

### If I Hit a Blocker

Example: FastEmbed library version incompatibility.

```
🚫 BLOCKED: crucible M2.4 (Embeddings)
Reason: FastEmbed 0.2.0 has breaking changes in ONNX model loading
Options:
  A) Pin to FastEmbed 0.1.5 (stable)
  B) Update code to FastEmbed 0.2.0 API
Recommendation: Option B (future-proof, Phase 1 compatible)
Awaiting: Your direction
```

### When Done

```
✅ crucible M2.X merged to main. Branch deleted.
Ready for crucible M2.Y or any other project.
```

---

## Approval & Review Expectations

### PR Review Workflow

1. I create PR → `status:review`
2. You review (or auto-approve if aligned)
3. If approved:
   - I merge (squash/rebase, no merge commits)
   - Delete feature branch
   - Close issue (auto-linked in PR)
4. If revisions needed:
   - You leave comments
   - I update branch with new commits
   - Ready for re-review

### Automated Checks (No Manual Approval Needed)

- Ruff linting (enforced via pre-commit)
- Pyright type checking (enforced in CI)
- Test coverage (≥ 80% gated by pytest)
- Build artifact generation

**You approve for:**
- Architecture alignment (cache design, routing strategy)
- Feature completeness (acceptance criteria met)
- Performance benchmarks (latency goals)
- Docs quality (README, ARCHITECTURE.md updates)

---

## Escalation & Decisions

If I encounter ambiguity mid-task:

```
❓ crucible M2.2 (Two-Tier Cache): Should we persist L2 semantic embeddings to disk by default?
Options:
  A) In-memory only (fast, but ephemeral)
  B) SQLite-vec persistent (durable, slower)
  C) Configurable (best flexibility)
Recommendation: Option C (align with Phase 2 cloud sync)
Awaiting: Your call
```

I'll propose and wait for your decision. Never assume design on Crucible.

---

## Examples: Full Work Cycles

### Example 1: Simple Feature (M2.3 — Request Normalization)

```
You: Work on crucible M2.3

Me: 
✓ Routing: ~/.openclaw/workspaces/crucible/
✓ Pre-work checklist passed (main clean, no open PRs)
✓ Branch created: feature/M2.3-request-normalizer
✓ Code written: src/crucible/core/normalizer.py
✓ Tests added: tests/test_normalizer.py (98% coverage)
✓ Build passing: ruff ✓ | pyright ✓ | pytest ✓
✓ PR created: #4 "M2.3: Request Normalization & Caching"
```

You review → approve → I merge → Issue #6 closes automatically.

---

### Example 2: Blocked Work (M2.4 — Embeddings)

```
You: Start crucible M2.4

Me:
✓ Pre-work checklist passed
✓ Branch created: feature/M2.4-embeddings
✗ BLOCKED: FastEmbed ONNX model loading
  (API incompatibility with installed version)

Status: status:blocked
Action: Needs version pin or API update decision
```

You decide → I resume → Complete as usual.

---

### Example 3: Performance-Critical Issue (M2.2 — Two-Tier Cache)

```
You: Finish crucible M2.2 with latency benchmarks

Me:
✓ L1 exact match implemented (0.8ms P50, 1.2ms P99)
✓ L2 semantic match implemented (12ms P50, 18ms P99)
✓ Benchmark suite added: test_benchmarks.py
✓ PR #7 includes performance profiles
✓ Ready for review
```

You approve latency targets → I merge → Issue closes.

---

## Workflow Summary

| Step | Owner | Input | Output |
|------|-------|-------|--------|
| 1. Route Project | Me | Project name (crucible) | Workspace path resolved |
| 2. Pick Issue | You | Issue number (M2.X or #Y) | "Got it, starting work" |
| 3. Pre-Check | Me | Issue details + workspace validation | Blockers identified or clear |
| 4. Code & Test | Me | Acceptance criteria | Feature branch with tests |
| 5. PR | Me | Code + tests | PR #N ready for review |
| 6. Review | You | PR changes | Approved or revision requests |
| 7. Merge | Me | Approval | Main updated, issue closed |
| 8. Report | Me | Completion | Ready for next issue |

---

## Crucible-Specific Notes

- **No Shared Dependencies:** Crucible has zero imports from Assay, flow-ledger, or other projects.
- **Pure Functional Core:** All business logic (similarity, normalization, routing) is pure Python—no I/O side effects.
- **Streaming-First:** Crucible must handle OpenAI SSE streaming correctly (chunk reconstruction, no latency penalty).
- **Pluggable Storage:** Storage backends are abstract—memory for MVP, SQLite-vec for persistent, Redis/Qdrant for Phase 2+.
- **Performance Budgets:** L1 < 1ms, L2 < 15ms. Benchmarks enforced in CI.

---

## Questions?

If you're unsure how to direct work on Crucible, default to:

```
Work on crucible M2.X
```

I'll handle the rest. This document is your reference for what happens behind the scenes.

---

**Ash, Primary Orchestrator**  
Crucible Project (v0.1.0-dev) — Independent Workspace  
Last Updated: 2026-08-30
