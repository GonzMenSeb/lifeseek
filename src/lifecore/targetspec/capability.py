"""Capability map (Task 2.4, SPEC §4.2) — the silent-failure killer.

``capable_engines(spec)`` is a pure function from a typed spec to the ordered list of
engines that can actually search for it. An **empty list** is a first-class, explicit
signal: the campaign returns ``no-capable-engine`` instead of a misleading "not found".
"""

from __future__ import annotations

from enum import StrEnum

from lifecore.targetspec.models import (
    Oscillator,
    OscillatorMechanism,
    SlopeClass,
    Spaceship,
    StillLife,
    TargetSpec,
)


class EngineId(StrEnum):
    QFIND = "qfind"
    RLIFESRC = "rlifesrc"
    LLS = "lls"
    IKPX2 = "ikpx2"


def capable_engines(spec: TargetSpec) -> list[EngineId]:
    """Engines capable of searching for ``spec``; ``[]`` means no-capable-engine."""
    if isinstance(spec, Spaceship):
        if spec.slope is SlopeClass.OBLIQUE:
            return [EngineId.IKPX2]  # stub in v1; routes correctly, no false 'not found'
        return [EngineId.QFIND, EngineId.RLIFESRC]  # orthogonal / diagonal
    if isinstance(spec, Oscillator):
        if spec.mechanism is OscillatorMechanism.LOW_PERIOD_DIRECT:
            return [EngineId.RLIFESRC, EngineId.LLS]
        return []  # assembly mechanisms: construction toolkits are LATER
    if isinstance(spec, StillLife):
        return [EngineId.RLIFESRC, EngineId.LLS]
    # Gun / Puffer / Rake / Eater stubs and anything unrecognized: no capability.
    return []
