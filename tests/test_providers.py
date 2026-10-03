"""Provider seam + cassette replay, including the dual-layout reader (spar condition 1)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from ailab_core.providers import (
    CassetteMissError,
    LLMProvider,
    OllamaProvider,
    ReplayProvider,
    SupportsTokenCounts,
    cassette_key,
)

MODEL = "gemma3:27b"
PROMPT = "Question: what is the capital?\nContext:\n[c0] Paris is the capital."
RESPONSE = "ANSWER: Paris\nCITE: c0"


def _entry() -> dict[str, object]:
    return {"model": MODEL, "response": RESPONSE, "prompt_eval_count": 42, "eval_count": 7}


def _write_flat(path: Path) -> None:
    """Legacy ailab-rag layout: a flat {key: entry} map, no header."""
    path.write_text(json.dumps({cassette_key(MODEL, PROMPT): _entry()}), encoding="utf-8")


def _write_header(path: Path) -> None:
    """ailab-prompting layout: a header plus an `entries` map."""
    payload = {
        "provider": "ollama",
        "model": MODEL,
        "model_digest": "a418f583",
        "entries": {cassette_key(MODEL, PROMPT): _entry()},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cassette_key_is_stable_and_order_independent() -> None:
    assert cassette_key(MODEL, PROMPT) == cassette_key(MODEL, PROMPT)
    assert cassette_key(MODEL, PROMPT) != cassette_key("other", PROMPT)


@pytest.mark.parametrize("writer", [_write_flat, _write_header])
def test_replay_reads_both_layouts_identically(
    tmp_path: Path, writer: Callable[[Path], None]
) -> None:
    path = tmp_path / "cassette.json"
    writer(path)
    rp = ReplayProvider(path, model=MODEL)
    assert rp.complete(PROMPT) == RESPONSE
    assert rp.token_counts(PROMPT) == (42, 7, False)
    assert rp.entry_count == 1
    assert rp.call_count == 1


def test_header_layout_sets_name_and_digest_from_header(tmp_path: Path) -> None:
    path = tmp_path / "cassette.json"
    _write_header(path)
    rp = ReplayProvider(path, model=MODEL)
    assert rp.name == "ollama"
    assert rp.model_digest == "a418f583"


def test_flat_layout_keeps_default_name_and_blank_digest(tmp_path: Path) -> None:
    path = tmp_path / "cassette.json"
    _write_flat(path)
    rp = ReplayProvider(path, name="replay", model=MODEL)
    assert rp.name == "replay"
    assert rp.model_digest == ""


def test_miss_raises_so_a_stale_cassette_cannot_pass(tmp_path: Path) -> None:
    path = tmp_path / "cassette.json"
    _write_flat(path)
    rp = ReplayProvider(path, model=MODEL)
    with pytest.raises(CassetteMissError):
        rp.complete("a prompt that was never recorded")


def test_replay_satisfies_both_protocols(tmp_path: Path) -> None:
    path = tmp_path / "cassette.json"
    _write_header(path)
    rp = ReplayProvider(path, model=MODEL)
    assert isinstance(rp, LLMProvider)
    assert isinstance(rp, SupportsTokenCounts)


def test_ollama_host_normalizes_without_network() -> None:
    bare = OllamaProvider("m", host="example.local:11434")
    assert bare.url == "http://example.local:11434/api/generate"
    trailing = OllamaProvider("m", host="http://h:1/")
    assert trailing.url == "http://h:1/api/generate"
    assert trailing.seed == OllamaProvider.DEFAULT_SEED
