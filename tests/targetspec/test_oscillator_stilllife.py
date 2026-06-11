"""Oscillator / StillLife / LATER-stub spec tests (Task 2.3)."""

import pytest

from lifecore.targetspec.models import (
    Eater,
    Gun,
    Oscillator,
    OscillatorMechanism,
    Puffer,
    Rake,
    SpecKind,
    StillLife,
    SymmetryClass,
)
from lifecore.targetspec.yaml_io import from_yaml, to_yaml


def test_oscillator_mechanism_enum() -> None:
    o = Oscillator(period=15, bbox_max=(8, 8))
    assert o.kind is SpecKind.OSCILLATOR
    assert o.mechanism is OscillatorMechanism.LOW_PERIOD_DIRECT  # default
    for m in OscillatorMechanism:
        assert Oscillator(period=30, mechanism=m, bbox_max=(8, 8)).mechanism is m
    with pytest.raises(ValueError):
        Oscillator(period=15, mechanism="nonexistent", bbox_max=(8, 8))  # type: ignore[arg-type]


def test_oscillator_rejects_period_one() -> None:
    with pytest.raises(ValueError):
        Oscillator(period=1, bbox_max=(8, 8))  # p=1 is a still life


def test_stilllife_fields_and_postfilter() -> None:
    s = StillLife(bbox_max=(6, 6), population_range=(4, 12), symmetry=SymmetryClass.BILATERAL_EVEN)
    assert s.kind is SpecKind.STILL_LIFE
    ep = s.engine_params()
    assert "population_range" not in ep  # post-hoc filter
    assert ep["bbox_max"] == (6, 6)  # engine input (SAT box)


def test_stub_types_constructible() -> None:
    assert Gun().kind is SpecKind.GUN
    assert Puffer().kind is SpecKind.PUFFER
    assert Rake().kind is SpecKind.RAKE
    assert Eater().kind is SpecKind.EATER


def test_yaml_roundtrip_oscillator_and_stilllife() -> None:
    for spec in (
        Oscillator(period=15, mechanism=OscillatorMechanism.PERIOD_MULTIPLIER, bbox_max=(8, 8)),
        StillLife(bbox_max=(5, 5), population_range=(4, 4)),
    ):
        back = from_yaml(to_yaml(spec))
        assert type(back) is type(spec)
        assert back == spec
        assert back.spec_id == spec.spec_id
