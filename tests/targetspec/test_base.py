"""Contract tests for the base TargetSpec + hashing + YAML io (Task 2.1)."""

import pytest

from lifecore.targetspec.hashing import canonical_json, spec_id_for
from lifecore.targetspec.models import SpecKind, TargetSpec
from lifecore.targetspec.yaml_io import from_yaml, to_yaml


class _DummySpec(TargetSpec):
    """Minimal concrete spec to exercise the base machinery (real types: 2.2/2.3)."""

    kind: SpecKind = SpecKind.STILL_LIFE
    bbox_max: tuple[int, int] = (4, 4)


def test_defaults() -> None:
    s = _DummySpec()
    assert s.rule == "B3/S23"
    assert s.kind == SpecKind.STILL_LIFE
    assert s.notes == ""


def test_spec_id_stable_across_key_order() -> None:
    a = canonical_json({"b": 1, "a": [3, 2], "c": {"y": 1, "x": 2}})
    b = canonical_json({"c": {"x": 2, "y": 1}, "a": [3, 2], "b": 1})
    assert a == b
    assert spec_id_for({"b": 1, "a": 2}) == spec_id_for({"a": 2, "b": 1})


def test_spec_id_is_sha256_hex() -> None:
    sid = _DummySpec().spec_id
    assert isinstance(sid, str) and len(sid) == 64
    int(sid, 16)  # valid hex


def test_spec_id_changes_with_content() -> None:
    assert _DummySpec(bbox_max=(4, 4)).spec_id != _DummySpec(bbox_max=(5, 5)).spec_id


def test_yaml_roundtrip_preserves_spec_id() -> None:
    s = _DummySpec(bbox_max=(6, 3), notes="hello")
    text = to_yaml(s)
    # _DummySpec shares the still_life kind with the real type, so pass it explicitly;
    # registry-based dispatch (from_yaml(text)) is covered by the real-type tests.
    back = from_yaml(text, _DummySpec)
    assert isinstance(back, _DummySpec)
    assert back == s
    assert back.spec_id == s.spec_id


def test_frozen_is_immutable() -> None:
    s = _DummySpec()
    with pytest.raises((TypeError, ValueError, AttributeError)):
        s.rule = "B36/S23"


def test_freeze_returns_immutable_copy() -> None:
    s = _DummySpec().freeze()
    with pytest.raises((TypeError, ValueError, AttributeError)):
        s.notes = "mutated"


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValueError):
        _DummySpec(unknown_field=1)  # type: ignore[call-arg]
