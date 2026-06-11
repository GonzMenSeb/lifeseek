"""Closed-world, type-specific verification gate (Task 3.1, SPEC §5).

Runs on the independent NumPy reference simulator ONLY (never lifelib) — verification
by a separate code path is the core trust guarantee (SPEC §1.2). The universal
protocol embeds the candidate in an unbounded field (the reference sim never clips),
requires an EXACT image at the claimed period with an EMPTY residual set (kills
debris/clipping loopholes), and confirms the TRUE minimal period (kills trivial-LCM
"oscillators"). Produces a signed :class:`VerificationRecord`.
"""

from __future__ import annotations

from lifecore.sim import reference
from lifecore.sim.pattern import Pattern
from lifecore.targetspec.models import Spaceship, TargetSpec
from lifecore.verify.records import (
    Verdict,
    VerificationRecord,
    reference_sim_version_hash,
)


def _minimal_translate_period(
    candidate: Pattern, max_period: int
) -> tuple[int | None, tuple[int, int] | None]:
    """Smallest q in 1..max_period with step(candidate, q) a pure translation of it.

    Returns (period, displacement) or (None, None) if no recurrence is found — i.e.
    the candidate is not a translating-periodic object within the horizon.
    """
    if candidate.is_empty:
        return None, None
    shape = candidate.normalize().cells
    bx, by, _, _ = candidate.bbox
    for q in range(1, max_period + 1):
        evolved = reference.step(candidate, q)
        if evolved.normalize().cells == shape:
            ex, ey, _, _ = evolved.bbox
            return q, (ex - bx, ey - by)
    return None, None


def _verify_spaceship(
    candidate: Pattern, spec: Spaceship, producer_engine_version_hash: str | None
) -> VerificationRecord:
    p = spec.period
    dx, dy = spec.displacement
    horizon = max(4 * p, p + 4)

    observed_period, observed_disp = _minimal_translate_period(candidate, horizon)

    # Exact-image-at-period with empty-residual assertion (kills debris/clipping).
    target = candidate.translate(dx, dy)
    moved = reference.step(candidate, p)
    residual = len(moved.cells ^ target.cells)

    # Confirm >= 2 full periods of clean recurrence.
    two_period_ok = (
        reference.step(candidate, 2 * p).cells == candidate.translate(2 * dx, 2 * dy).cells
    )

    is_true_period = observed_period == p and observed_disp == (dx, dy)
    passed = residual == 0 and is_true_period and two_period_ok and not candidate.is_empty

    notes = []
    if candidate.is_empty:
        notes.append("empty candidate")
    if residual != 0:
        notes.append(f"non-empty residual ({residual} cells) at period {p}")
    if observed_period is not None and observed_period != p:
        notes.append(f"true minimal period is {observed_period}, not claimed {p}")
    if observed_period is None:
        notes.append("no translating-periodic recurrence within horizon")
    if observed_disp is not None and observed_disp != (dx, dy):
        notes.append(f"observed displacement {observed_disp} != claimed {(dx, dy)}")
    if not two_period_ok:
        notes.append("failed >=2-period recurrence confirmation")

    margin = max(abs(dx), abs(dy)) * p + (candidate.width + candidate.height)
    record = VerificationRecord(
        spec_id=spec.spec_id,
        rule=spec.rule,
        verdict=Verdict.PASS if passed else Verdict.REJECT,
        claimed_period=p,
        observed_period=observed_period,
        claimed_displacement=(dx, dy),
        observed_displacement=observed_disp,
        residual_cell_count=residual,
        field_size=(candidate.width, candidate.height),
        margin=margin,
        t_settle=0,
        reference_sim_version_hash=reference_sim_version_hash(),
        producer_engine_version_hash=producer_engine_version_hash,
        notes="; ".join(notes),
    )
    return record.signed()


def verify(
    candidate: Pattern,
    spec: TargetSpec,
    producer_engine_version_hash: str | None = None,
) -> VerificationRecord:
    """Verify ``candidate`` against ``spec`` on the reference path; return a signed record."""
    if candidate.rule != spec.rule:
        candidate = candidate.with_rule(spec.rule)
    if isinstance(spec, Spaceship):
        return _verify_spaceship(candidate, spec, producer_engine_version_hash)
    raise NotImplementedError(f"verification not implemented for spec kind {spec.kind!r}")
