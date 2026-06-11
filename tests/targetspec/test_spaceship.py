"""Spaceship spec tests (Task 2.2) — mechanism-faithful, SPEC §4.1."""

import pytest

from lifecore.targetspec.models import SlopeClass, Spaceship, SpecKind, SymmetryClass
from lifecore.targetspec.yaml_io import from_yaml, to_yaml


def mk(dx: int, dy: int, p: int, **kw: object) -> Spaceship:
    kw.setdefault("symmetry_class", SymmetryClass.ASYMMETRIC)
    kw.setdefault("search_width", (1, 6))
    return Spaceship(displacement=(dx, dy), period=p, **kw)  # type: ignore[arg-type]


def test_slope_classification() -> None:
    assert mk(2, 0, 4).slope is SlopeClass.ORTHOGONAL
    assert mk(0, 3, 6).slope is SlopeClass.ORTHOGONAL
    assert mk(1, 1, 4).slope is SlopeClass.DIAGONAL
    assert mk(2, 1, 7).slope is SlopeClass.OBLIQUE


def test_velocity_strings() -> None:
    assert mk(2, 0, 4).velocity == "c/2 orthogonal"
    assert mk(1, 1, 4).velocity == "c/4 diagonal"
    assert mk(2, 1, 7).velocity == "(2,1)c/7 oblique"


def test_kind_and_defaults() -> None:
    s = mk(1, 1, 4)
    assert s.kind is SpecKind.SPACESHIP
    assert s.population_range is None and s.bbox_max is None


def test_population_is_postfilter_not_engine_input() -> None:
    s = mk(1, 1, 4, population_range=(1, 20), bbox_max=(10, 10))
    ep = s.engine_params()
    assert "population_range" not in ep
    assert "bbox_max" not in ep
    # engine inputs that MUST be present
    assert ep["search_width"] == (1, 6)
    assert ep["displacement"] == (1, 1)
    assert ep["period"] == 4


def test_reject_width_inverted() -> None:
    with pytest.raises(ValueError):
        mk(1, 1, 4, search_width=(6, 1))


def test_reject_zero_displacement() -> None:
    with pytest.raises(ValueError):
        mk(0, 0, 4)


def test_reject_faster_than_light() -> None:
    with pytest.raises(ValueError):
        mk(3, 0, 2)  # 3 cells in 2 gens > c


def test_yaml_roundtrip_dispatches_by_kind() -> None:
    s = mk(1, 1, 4, population_range=(5, 5))
    back = from_yaml(to_yaml(s))
    assert isinstance(back, Spaceship)
    assert back == s
    assert back.spec_id == s.spec_id
