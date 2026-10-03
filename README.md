# ailab-core

Shared, discipline-agnostic core for the `ailab-*` labs. It holds the machinery every lab needs
but none should re-implement:

- **Provider seam** (`ailab_core.providers`): a narrow `LLMProvider` protocol, an optional
  `SupportsTokenCounts` capability, a `ReplayProvider` that serves a committed JSON cassette (a
  miss raises, so a stale cassette can never silently pass), and an `OllamaProvider` for recording
  cassettes from a local model. Stdlib only.
- **Gate primitives** (`ailab_core.gate`): a tolerance-band `floor_breach` check, a fail-closed
  `require_metrics` presence check, and a `GateResult` accumulator. These give the shared shape of
  a regression gate. Each lab still owns its own domain gate (which metrics, which floors).

## Why this exists

Three labs (`ailab-evals`, `ailab-rag`, `ailab-prompting`) had drifted copies of the same provider
and cassette code. The copy tax grows with each new lab, so the rule recorded in both labs'
`docs/DESIGN.md` is: no fourth lab until this shared core exists and the existing labs depend on it.

## Install

```
uv add "ailab-core @ git+https://github.com/andrewjpyle/ailab-core@<commit-sha>"
```

Pin an immutable commit SHA, not a branch or tag.

## Non-goals

No plugin system, no config framework, no CLI. The surface stays small on purpose.

## Develop

```
make install   # uv sync --locked
make lint       # ruff + mypy strict
make test       # pytest + coverage (fails under 90%)
make scan       # gitleaks + denylist
```
