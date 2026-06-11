from __future__ import annotations

from lifecore.strategy.battery import (
    BATTERY,
    BatterySpec,
    Reachability,
    reachable_specs,
    unsat_specs,
)
from lifecore.targetspec.models import TargetSpec


def test_battery_has_both_tags() -> None:
    assert len(BATTERY) >= 12
    tags = {b.reachability for b in BATTERY}
    assert Reachability.REACHABLE in tags
    assert Reachability.UNSAT in tags
    assert sum(1 for b in BATTERY if b.reachability is Reachability.REACHABLE) >= 1
    assert sum(1 for b in BATTERY if b.reachability is Reachability.UNSAT) >= 1


def test_all_specs_constructible_and_have_sources() -> None:
    for entry in BATTERY:
        assert isinstance(entry, BatterySpec)
        assert isinstance(entry.spec, TargetSpec)
        assert entry.source != ""
        # spec_id is derivable => spec is fully constructed/valid
        assert entry.spec.spec_id


def test_reachable_and_unsat_partition() -> None:
    reachable = reachable_specs()
    unsat = unsat_specs()
    assert all(b.reachability is Reachability.REACHABLE for b in reachable)
    assert all(b.reachability is Reachability.UNSAT for b in unsat)
    # partition: disjoint and together cover BATTERY
    assert len(reachable) + len(unsat) == len(BATTERY)
    assert set(reachable).isdisjoint(set(unsat))
    assert set(reachable) | set(unsat) == set(BATTERY)
