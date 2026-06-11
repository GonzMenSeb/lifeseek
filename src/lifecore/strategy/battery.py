"""Fixed reference battery of target specs for meta-evaluation (SPEC §7).

A small, hand-curated set of specs whose answer is *known a priori* — either a famous
realizable object (REACHABLE) or a constructible-but-genuinely-impossible request
(UNSAT). The battery is the ground truth against which the self-improvement loop is
scored: a search node is only rewarded for verified-novel discoveries and for
*correctly proving non-existence* on the UNSAT entries — never for thrashing.

Every entry carries a ``source`` citation so the tag can be audited:
- REACHABLE entries cite the canonical object name (e.g. "Conway's glider").
- UNSAT entries cite a brief geometric/parity reason for impossibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lifecore.targetspec.models import (
    Oscillator,
    Spaceship,
    StillLife,
    SymmetryClass,
    TargetSpec,
)


class Reachability(StrEnum):
    REACHABLE = "reachable"
    UNSAT = "unsat"


@dataclass(frozen=True)
class BatterySpec:
    spec: TargetSpec
    reachability: Reachability
    source: str
    notes: str = ""


BATTERY: tuple[BatterySpec, ...] = (
    # ---- REACHABLE: famous, well-attested objects ----
    BatterySpec(
        spec=Spaceship(
            displacement=(1, 1),
            period=4,
            symmetry_class=SymmetryClass.GLIDE_REFLECT,
            search_width=(1, 5),
        ),
        reachability=Reachability.REACHABLE,
        source="Conway's glider (c/4 diagonal, 1970)",
        notes="The canonical Life spaceship.",
    ),
    BatterySpec(
        spec=Spaceship(
            displacement=(2, 0),
            period=4,
            symmetry_class=SymmetryClass.BILATERAL_EVEN,
            search_width=(1, 6),
        ),
        reachability=Reachability.REACHABLE,
        source="Lightweight spaceship (LWSS), Conway 1970 (c/2 orthogonal)",
    ),
    BatterySpec(
        spec=Spaceship(
            displacement=(2, 0),
            period=4,
            symmetry_class=SymmetryClass.ASYMMETRIC,
            search_width=(1, 8),
        ),
        reachability=Reachability.REACHABLE,
        source="Middleweight spaceship (MWSS), c/2 orthogonal",
    ),
    BatterySpec(
        spec=Oscillator(period=2, bbox_max=(3, 3)),
        reachability=Reachability.REACHABLE,
        source="Blinker (p2), Conway 1970",
    ),
    BatterySpec(
        spec=Oscillator(period=2, bbox_max=(4, 4)),
        reachability=Reachability.REACHABLE,
        source="Toad (p2), Conway 1970",
    ),
    BatterySpec(
        spec=Oscillator(period=2, bbox_max=(3, 3), symmetry=SymmetryClass.BILATERAL_EVEN),
        reachability=Reachability.REACHABLE,
        source="Beacon (p2)",
    ),
    BatterySpec(
        spec=Oscillator(period=15, bbox_max=(10, 3)),
        reachability=Reachability.REACHABLE,
        source="Pentadecathlon (p15), 1970 (fits in a 10x3 bounding box)",
    ),
    BatterySpec(
        spec=StillLife(bbox_max=(2, 2)),
        reachability=Reachability.REACHABLE,
        source="Block (2x2 still life)",
    ),
    BatterySpec(
        spec=StillLife(bbox_max=(4, 3)),
        reachability=Reachability.REACHABLE,
        source="Beehive (still life, 4x3 bounding box)",
    ),
    BatterySpec(
        spec=StillLife(bbox_max=(4, 4)),
        reachability=Reachability.REACHABLE,
        source="Loaf (still life, fits 4x4)",
    ),
    # ---- UNSAT: constructible specs that are genuinely impossible ----
    BatterySpec(
        spec=StillLife(bbox_max=(1, 1)),
        reachability=Reachability.UNSAT,
        source="known-UNSAT: no still life fits in a 1x1 box",
        notes="A single live cell has 0 live neighbours and dies; minimum still life is the 2x2 block.",
    ),
    BatterySpec(
        spec=StillLife(bbox_max=(2, 1)),
        reachability=Reachability.UNSAT,
        source="known-UNSAT: no still life fits in a 2x1 box",
        notes="Two cells in a line each have <2 neighbours and die; no stable pattern is that thin.",
    ),
    BatterySpec(
        spec=Oscillator(period=2, bbox_max=(1, 1)),
        reachability=Reachability.UNSAT,
        source="known-UNSAT: no p2 oscillator fits in a 1x1 box",
        notes="A 1x1 box can hold at most one cell, which simply dies; no oscillation possible.",
    ),
    BatterySpec(
        spec=Oscillator(period=2, bbox_max=(2, 1)),
        reachability=Reachability.UNSAT,
        source="known-UNSAT: no p2 oscillator fits in a 2x1 box",
        notes="The smallest p2 oscillator (blinker) needs a 3x3 box; a 2x1 box cannot host any oscillation.",
    ),
    BatterySpec(
        spec=Spaceship(
            displacement=(1, 0),
            period=2,
            symmetry_class=SymmetryClass.ASYMMETRIC,
            search_width=(1, 1),
        ),
        reachability=Reachability.UNSAT,
        source="known-UNSAT: no c/2 orthogonal spaceship within search width 1",
        notes="Width-1 patterns cannot sustain a translating front; minimal orthogonal ships are far wider.",
    ),
)


def reachable_specs() -> tuple[BatterySpec, ...]:
    return tuple(b for b in BATTERY if b.reachability is Reachability.REACHABLE)


def unsat_specs() -> tuple[BatterySpec, ...]:
    return tuple(b for b in BATTERY if b.reachability is Reachability.UNSAT)
