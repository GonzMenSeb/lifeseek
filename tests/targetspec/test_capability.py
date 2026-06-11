"""Capability-map tests (Task 2.4) — no false 'not found' (SPEC §4.2)."""

from lifecore.targetspec.capability import EngineId, capable_engines
from lifecore.targetspec.models import (
    Eater,
    Gun,
    Oscillator,
    OscillatorMechanism,
    Puffer,
    Rake,
    Spaceship,
    StillLife,
    SymmetryClass,
)


def ship(dx: int, dy: int, p: int) -> Spaceship:
    return Spaceship(
        displacement=(dx, dy),
        period=p,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(1, 6),
    )


def test_orthogonal_and_diagonal_route_to_qfind_rlifesrc() -> None:
    assert capable_engines(ship(2, 0, 4)) == [EngineId.QFIND, EngineId.RLIFESRC]
    assert capable_engines(ship(1, 1, 4)) == [EngineId.QFIND, EngineId.RLIFESRC]


def test_oblique_routes_to_ikpx2() -> None:
    assert capable_engines(ship(2, 1, 7)) == [EngineId.IKPX2]


def test_low_period_oscillator_and_stilllife() -> None:
    osc = Oscillator(period=3, mechanism=OscillatorMechanism.LOW_PERIOD_DIRECT, bbox_max=(8, 8))
    assert capable_engines(osc) == [EngineId.RLIFESRC, EngineId.LLS]
    assert capable_engines(StillLife(bbox_max=(6, 6))) == [EngineId.RLIFESRC, EngineId.LLS]


def test_assembly_mechanism_oscillator_has_no_capability() -> None:
    for m in (
        OscillatorMechanism.HASSLER_CATALYST,
        OscillatorMechanism.PERIOD_MULTIPLIER,
        OscillatorMechanism.SIGNAL_LOOP_CONDUIT,
    ):
        assert capable_engines(Oscillator(period=30, mechanism=m, bbox_max=(8, 8))) == []


def test_stub_types_return_no_capability() -> None:
    for stub in (Gun(), Puffer(), Rake(), Eater()):
        assert capable_engines(stub) == []


def test_empty_means_no_capable_engine() -> None:
    # the contract the campaign relies on: [] is a distinct, explicit signal
    assert capable_engines(Gun()) == []
    assert capable_engines(ship(1, 1, 4)) != []
