"""Distilled cross-session failure memory (SPEC §7).

A :class:`FailureEnvelope` records a *region* of the search space that was proven UNSAT
across a set of engines at some budget — e.g. "c/5 orthogonal under width 20 is UNSAT
across qfind+rlifesrc at budget B". Planning reads this memory *before* committing
budget, so the loop does not re-explore a region already known (from a prior session)
to be a dead-end inside the same envelope.

Relevance is per spec kind:
- Spaceship: same ``slope`` and *width-subsumption* — the spec's requested
  ``search_width`` upper bound lies within the envelope's explored ``max_width``, so the
  spec is fully contained in the known-UNSAT region.
- Oscillator: ``period`` falls inside the envelope's explored period band, and the
  spec's bbox is within the explored ``max_bbox`` (if recorded).
- StillLife: the spec's bbox is subsumed by the envelope's explored ``max_bbox``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lifecore.targetspec.models import Oscillator, Spaceship, StillLife, TargetSpec


@dataclass(frozen=True)
class FailureEnvelope:
    spec_kind: str
    descriptor: dict[str, Any]
    engines: tuple[str, ...]
    budget: float
    source: str = ""


def _bbox_upper(bbox: tuple[int, int] | None) -> int | None:
    """The dominant bbox dimension (max of the two), or None if unconstrained."""
    return max(bbox) if bbox is not None else None


def _bbox_subsumed(spec_bbox: tuple[int, int] | None, env_max: Any) -> bool:
    """True iff the spec's bbox lies within the envelope's explored max bbox.

    An unbounded spec bbox can never be subsumed by a finite envelope.
    """
    if env_max is None:
        return False
    spec_upper = _bbox_upper(spec_bbox)
    if spec_upper is None:
        return False
    env_upper = max(int(env_max[0]), int(env_max[1]))
    return spec_upper <= env_upper


class FailureMemory:
    """Append-only store of UNSAT envelopes, queryable by spec relevance."""

    def __init__(self) -> None:
        self._envelopes: list[FailureEnvelope] = []

    def record(self, envelope: FailureEnvelope) -> None:
        self._envelopes.append(envelope)

    def all_envelopes(self) -> tuple[FailureEnvelope, ...]:
        return tuple(self._envelopes)

    def get_relevant(self, spec: TargetSpec) -> list[FailureEnvelope]:
        """Prior UNSAT envelopes that subsume ``spec`` (so the spec is a known dead-end)."""
        return [e for e in self._envelopes if self._is_relevant(e, spec)]

    @staticmethod
    def _is_relevant(env: FailureEnvelope, spec: TargetSpec) -> bool:
        if env.spec_kind != spec.kind.value:
            return False
        if isinstance(spec, Spaceship):
            if env.descriptor.get("slope") != spec.slope.value:
                return False
            max_width = env.descriptor.get("max_width")
            if max_width is None:
                return False
            # Width-subsumption: the spec's requested upper width is inside the
            # explored (and exhausted) width band.
            return spec.search_width[1] <= int(max_width)
        if isinstance(spec, Oscillator):
            p_min = env.descriptor.get("period_min")
            p_max = env.descriptor.get("period_max")
            if p_min is None or p_max is None:
                return False
            if not (int(p_min) <= spec.period <= int(p_max)):
                return False
            env_bbox = env.descriptor.get("max_bbox")
            if env_bbox is None:
                return True  # period band matched, no bbox constraint recorded
            return _bbox_subsumed(spec.bbox_max, env_bbox)
        if isinstance(spec, StillLife):
            return _bbox_subsumed(spec.bbox_max, env.descriptor.get("max_bbox"))
        return False
