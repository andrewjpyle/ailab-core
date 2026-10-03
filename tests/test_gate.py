"""Gate primitives: tolerance band + fail-closed presence (spar condition 3)."""

from __future__ import annotations

from ailab_core.gate import GateResult, floor_breach, require_metrics


def test_floor_breach_passes_within_tolerance_band() -> None:
    assert floor_breach("recall@5", 0.80, 0.80) is None
    assert floor_breach("recall@5", 0.79, 0.80, tolerance=0.02) is None  # within band


def test_floor_breach_fails_below_band_and_names_the_metric() -> None:
    msg = floor_breach("recall@5", 0.70, 0.80, tolerance=0.02)
    assert msg is not None
    assert "recall@5" in msg  # prove_gate.sh greps for the failing metric token


def test_floor_breach_fails_closed_on_missing_score() -> None:
    msg = floor_breach("field_accuracy", None, 0.80)
    assert msg is not None
    assert "fail-closed" in msg


def test_floor_breach_treats_nonpositive_floor_as_unenforced() -> None:
    assert floor_breach("optional", None, 0.0) is None
    assert floor_breach("optional", 0.0, -1.0) is None


def test_require_metrics_fails_closed_on_empty_or_absent() -> None:
    assert require_metrics({}, ["a"]) == ["no metrics to gate (expected ['a']); fail-closed"]
    assert require_metrics(None, ["a"]) == ["no metrics to gate (expected ['a']); fail-closed"]


def test_require_metrics_flags_each_missing_or_null_key() -> None:
    out = require_metrics({"a": 1.0, "b": None}, ["a", "b", "c"])
    assert any("'b'" in m for m in out)
    assert any("'c'" in m for m in out)
    assert all("'a'" not in m for m in out)


def test_require_metrics_passes_when_all_present() -> None:
    assert require_metrics({"a": 1.0, "b": 0.0}, ["a", "b"]) == []


def test_gate_result_accumulates_and_ignores_none() -> None:
    gate = GateResult()
    assert gate.passed
    gate.add(None)  # a passing check contributes nothing
    assert gate.passed
    gate.add(floor_breach("mrr", 0.1, 0.5))
    assert not gate.passed
    assert len(gate.failures) == 1
