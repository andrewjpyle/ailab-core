"""Shared LLM provider seam for the ailab-* labs. Stdlib only: no SDKs, no third-party HTTP.

This is the reconciled superset of the per-lab ``providers.py`` modules (ailab-rag @ 75dc602,
ailab-prompting @ 8c0ce34): the cassette key, :class:`CassetteMissError`, :class:`ReplayProvider`
and :class:`OllamaProvider` are discipline-agnostic and live here. Each lab keeps its own
``StubProvider`` (the stub's output is domain-specific: a Reader span for RAG, a fixed record
for extraction).

* :class:`LLMProvider` is the minimum protocol: ``name``, ``model`` and ``complete``.
* :class:`SupportsTokenCounts` is an OPTIONAL capability: a provider that can report vendor token
  counts for a cost axis. A lab that does not need the cost axis (e.g. RAG) need not implement it.
* :class:`ReplayProvider` serves a committed JSON cassette keyed by ``sha256(model, prompt)``. A
  miss RAISES, so a stale cassette can never silently pass. It reads BOTH the legacy flat layout
  ``{key: entry}`` and the header layout ``{header..., "entries": {key: entry}}``.
* :class:`OllamaProvider` POSTs to a local Ollama server with ``urllib`` from stdlib, used only in
  record mode to fill a cassette. The host comes from ``OLLAMA_HOST`` and is never stored.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """The minimum a text-completion backend must offer.

    A real implementation wraps a vendor SDK or a local model server and reads its credentials
    from the environment. Keeping the protocol this narrow is what makes providers swappable and
    the eval reproducible.
    """

    name: str  # provider id recorded in results, e.g. "stub" or "ollama"
    model: str

    def complete(self, prompt: str) -> str: ...


@runtime_checkable
class SupportsTokenCounts(Protocol):
    """Optional capability: report ``(prompt_tokens, completion_tokens, is_estimate)``.

    A lab with a cost axis (e.g. prompt engineering) implements this on its providers; a lab
    without one (e.g. retrieval) does not. Call sites should guard with
    ``isinstance(provider, SupportsTokenCounts)`` rather than assume it.
    """

    def token_counts(self, prompt: str) -> tuple[int, int, bool]: ...


def cassette_key(model: str, prompt: str) -> str:
    """Stable key for a cassette entry: ``sha256(model, prompt)``."""
    raw = json.dumps([model, prompt], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CassetteMissError(RuntimeError):
    """Raised when a ReplayProvider is asked for a prompt its cassette does not hold."""


class ReplayProvider:
    """Replay a committed JSON cassette; a miss raises so a stale cassette cannot pass.

    The cassette is EITHER the legacy flat layout (``{sha256(model, prompt): entry}``) OR the
    header layout (``{"provider", "model", "model_digest", ...: ..., "entries": {key: entry}}``).
    An entry is ``{"model", "response", ["prompt_eval_count", "eval_count"]}``. ``name`` mirrors
    the recorded ``provider`` (header layout) so the results record names what was replayed.
    """

    def __init__(self, path: str | Path, name: str = "replay", model: str = "replay") -> None:
        self.path = Path(path)
        self.model = model
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        entries = raw.get("entries") if isinstance(raw, dict) else None
        self._entries: dict[str, dict[str, Any]]
        if isinstance(entries, dict):  # header layout
            self.name = str(raw.get("provider", name))
            self.model_digest = str(raw.get("model_digest", ""))
            self._entries = entries
        else:  # legacy flat layout
            self.name = name
            self.model_digest = ""
            self._entries = raw
        self.calls = 0

    def _hit(self, prompt: str) -> dict[str, Any]:
        key = cassette_key(self.model, prompt)
        hit = self._entries.get(key)
        if hit is None:
            raise CassetteMissError(
                f"cassette miss for model {self.model!r} (prompt-hash {key}); "
                "re-record the cassette with `make record`"
            )
        return hit

    def complete(self, prompt: str) -> str:
        entry = self._hit(prompt)
        self.calls += 1
        return str(entry["response"])

    def token_counts(self, prompt: str) -> tuple[int, int, bool]:
        entry = self._hit(prompt)
        return (
            int(entry.get("prompt_eval_count", 0) or 0),
            int(entry.get("eval_count", 0) or 0),
            False,  # vendor counts, not an estimate
        )

    @property
    def call_count(self) -> int:
        return self.calls

    @property
    def entry_count(self) -> int:
        return len(self._entries)


class OllamaProvider:
    """Local models via Ollama ``/api/generate``. Used only in record mode. Stdlib HTTP.

    The server address comes from ``OLLAMA_HOST`` (default ``http://localhost:11434``, never a
    committed tailnet host) and is never stored. Generation is pinned to ``temperature`` 0 and a
    fixed ``seed`` so a re-record is deterministic, which keeps the replayed numbers stable.
    """

    name = "ollama"
    DEFAULT_SEED = 7

    def __init__(
        self, model: str, host: str | None = None, timeout: float = 300.0, seed: int = DEFAULT_SEED
    ) -> None:
        self.model = model
        base = host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
        if not base.startswith("http"):
            base = "http://" + base
        self.base = base.rstrip("/")
        self.url = self.base + "/api/generate"
        self.timeout = timeout
        self.seed = seed

    def generate(self, prompt: str) -> dict[str, Any]:
        """Return the raw Ollama response dict (text plus vendor token counts)."""
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0, "seed": self.seed},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data: dict[str, Any] = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - network
            raise RuntimeError(f"ollama: {exc}") from exc
        return data

    def complete(self, prompt: str) -> str:
        return str(self.generate(prompt).get("response", ""))

    def token_counts(self, prompt: str) -> tuple[int, int, bool]:  # pragma: no cover - network
        raw = self.generate(prompt)
        return (
            int(raw.get("prompt_eval_count", 0) or 0),
            int(raw.get("eval_count", 0) or 0),
            False,
        )
