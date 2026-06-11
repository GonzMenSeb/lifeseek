from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lifecore.strategy.failure_memory import FailureEnvelope, FailureMemory
from lifecore.targetspec.models import (
    Oscillator,
    Spaceship,
    StillLife,
    SymmetryClass,
)


def test_record_and_get_relevant_spaceship() -> None:
    mem = FailureMemory()
    mem.record(
        FailureEnvelope(
            spec_kind="spaceship",
            descriptor={"slope": "orthogonal", "velocity_class": "c/5", "max_width": 20},
            engines=("qfind", "rlifesrc"),
            budget=1_000.0,
            source="c/5 orthogonal under width 20 UNSAT across qfind+rlifesrc",
        )
    )

    # An orthogonal ship whose search width is within 20 is inside the UNSAT envelope.
    inside = Spaceship(
        displacement=(1, 0),
        period=5,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(1, 18),
    )
    assert len(mem.get_relevant(inside)) == 1

    # A diagonal ship is a different slope region -> not subsumed.
    diagonal = Spaceship(
        displacement=(1, 1),
        period=5,
        symmetry_class=SymmetryClass.GLIDE_REFLECT,
        search_width=(1, 18),
    )
    assert mem.get_relevant(diagonal) == []

    # An orthogonal ship asking for width *beyond* the explored envelope is not subsumed.
    wider = Spaceship(
        displacement=(1, 0),
        period=5,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(1, 40),
    )
    assert mem.get_relevant(wider) == []


def test_irrelevant_kind_not_returned() -> None:
    mem = FailureMemory()
    mem.record(
        FailureEnvelope(
            spec_kind="spaceship",
            descriptor={"slope": "orthogonal", "max_width": 20},
            engines=("qfind",),
            budget=10.0,
        )
    )
    osc = Oscillator(period=3, bbox_max=(5, 5))
    sl = StillLife(bbox_max=(3, 3))
    assert mem.get_relevant(osc) == []
    assert mem.get_relevant(sl) == []


def test_oscillator_and_stilllife_relevance() -> None:
    mem = FailureMemory()
    mem.record(
        FailureEnvelope(
            spec_kind="oscillator",
            descriptor={"period_min": 3, "period_max": 8, "max_bbox": [6, 6]},
            engines=("rlifesrc",),
            budget=50.0,
        )
    )
    mem.record(
        FailureEnvelope(
            spec_kind="still_life",
            descriptor={"max_bbox": [4, 4]},
            engines=("lls",),
            budget=5.0,
        )
    )

    # Oscillator inside the period band and bbox -> relevant.
    assert len(mem.get_relevant(Oscillator(period=5, bbox_max=(5, 5)))) == 1
    # Outside the period band -> not relevant.
    assert mem.get_relevant(Oscillator(period=20, bbox_max=(5, 5))) == []

    # Still life within the bbox envelope -> relevant.
    assert len(mem.get_relevant(StillLife(bbox_max=(3, 3)))) == 1
    # Still life larger than the explored bbox -> not subsumed.
    assert mem.get_relevant(StillLife(bbox_max=(9, 9))) == []


def test_memory_is_append_only() -> None:
    mem = FailureMemory()
    env = FailureEnvelope(
        spec_kind="still_life",
        descriptor={"max_bbox": [4, 4]},
        engines=("lls",),
        budget=5.0,
    )
    mem.record(env)
    assert len(mem.all_envelopes()) == 1
    mem.record(env)
    assert len(mem.all_envelopes()) == 2
    assert isinstance(mem.all_envelopes(), tuple)

    with pytest.raises(FrozenInstanceError):
        env.budget = 99.0  # type: ignore[misc]
