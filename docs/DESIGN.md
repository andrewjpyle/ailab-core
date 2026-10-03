# DESIGN

## What this is

`ailab-core` is the shared core extracted from the `ailab-*` discipline labs. It was built by
reconciling the drifted copies in `ailab-rag` (at commit 75dc602) and `ailab-prompting` (at commit
8c0ce34), not by copying one lab's version.

## 1. The surface is deliberately narrow

Only three things are shared across disciplines, so only three things live here:

1. The provider seam and cassette replay.
2. The `OllamaProvider` used to record a cassette from a local model.
3. The regression-gate primitives (the tolerance-band check and the fail-closed presence check).

Non-goals: no plugin system, no config framework, no CLI, no dependencies. Each lab keeps its own
`StubProvider` (its output is domain-specific), its own metrics, and its own domain gate.

## 2. The provider protocol is a superset, split by capability

`ailab-prompting` added a cost axis and so added `token_counts` to its provider; `ailab-rag` never
needed it. Forcing every provider to implement `token_counts` would be over-abstraction. So the
core splits the protocol:

- `LLMProvider`: `name`, `model`, `complete`. The minimum.
- `SupportsTokenCounts`: an optional `token_counts` capability. A call site guards with
  `isinstance(provider, SupportsTokenCounts)` instead of assuming it.

## 3. The cassette reader accepts both layouts

The two labs used different cassette layouts: `ailab-rag` wrote a flat `{key: entry}` map;
`ailab-prompting` wrote a header plus an `entries` map. `ReplayProvider` reads BOTH and writes only
the newer header layout, so no committed cassette has to be re-recorded to adopt the core. A miss
still raises `CassetteMissError`, so a stale cassette can never pass.

## 4. The gate fails closed

`floor_breach` treats a missing (None) score against an enforced floor as a failure, not a skip.
`require_metrics` treats an empty or absent metric mapping as a failure. A gate that cannot see a
metric must not pass. Each lab builds its domain gate from these primitives plus its own rules.

## 5. The denylist and content rules travel with the family

The `secret-scan` CI job (gitleaks plus `scripts/denylist_scan.sh`) and the no-em-dash doc rule are
the same guards every `ailab-*` repo carries. The private denylist comes from the `AILAB_DENYLIST`
Actions secret and is never committed.
