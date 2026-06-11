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
from lifecore.sim.pattern import Cell, Pattern
from lifecore.targetspec.models import Oscillator, Spaceship, StillLife, TargetSpec
from lifecore.verify.records import (
    OrphanWitness,
    Verdict,
    VerificationRecord,
    reference_sim_version_hash,
)

GOE_MIN_PADDING = 4  # SPEC §5.2: orphan witness needs a forced-dead border of thickness >= 4


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
        claim="spaceship",
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


def _minimal_stationary_period(candidate: Pattern, max_period: int) -> int | None:
    """Smallest q with step(candidate, q) == candidate exactly (stationary recurrence)."""
    for q in range(1, max_period + 1):
        if reference.step(candidate, q).cells == candidate.cells:
            return q
    return None


def _phase_cells(candidate: Pattern, period: int) -> list[frozenset[Cell]]:
    return [reference.step(candidate, i).cells for i in range(period)]


def _has_full_period_cell(phases: list[frozenset[Cell]], period: int) -> bool:
    """True iff some cell's on/off sequence has minimal cyclic period exactly ``period``.

    This is the true-period guarantee: it rejects a 'period p' that is merely the LCM of
    separable sub-oscillators, where every cell's individual period is a proper divisor of p.
    """
    proper_divisors = [d for d in range(1, period) if period % d == 0]
    union: set[Cell] = set().union(*phases) if phases else set()
    for cell in union:
        vec = [cell in ph for ph in phases]
        is_full = not any(
            all(vec[k] == vec[(k + d) % period] for k in range(period)) for d in proper_divisors
        )
        if is_full:
            return True
    return False


def _verify_oscillator(
    candidate: Pattern, spec: Oscillator, producer_engine_version_hash: str | None
) -> VerificationRecord:
    p = spec.period
    horizon = max(2 * p, p + 4)

    observed_period = _minimal_stationary_period(candidate, horizon)
    moved = reference.step(candidate, p)
    residual = len(moved.cells ^ candidate.cells)  # oscillator displacement is (0,0)

    phases = _phase_cells(candidate, p) if not candidate.is_empty else []
    stator = set(phases[0]).intersection(*phases) if phases else set()
    union: set[Cell] = set().union(*phases) if phases else set()
    rotor = union - stator
    genuine_full_period = not candidate.is_empty and _has_full_period_cell(phases, p)
    two_period_ok = reference.step(candidate, 2 * p).cells == candidate.cells

    passed = (
        residual == 0
        and observed_period == p
        and genuine_full_period
        and two_period_ok
        and not candidate.is_empty
    )

    notes = []
    if candidate.is_empty:
        notes.append("empty candidate")
    if residual != 0:
        notes.append(f"non-empty residual ({residual}) — not stationary at period {p}")
    if observed_period is None:
        notes.append("no stationary recurrence within horizon (not an oscillator)")
    elif observed_period != p:
        notes.append(f"true minimal period is {observed_period}, not claimed {p}")
    if observed_period == p and not genuine_full_period:
        notes.append(
            f"no single cell oscillates at the full claimed period {p} "
            "(trivial LCM of separable sub-oscillators)"
        )
    if not two_period_ok:
        notes.append("failed >=2-period recurrence confirmation")

    record = VerificationRecord(
        spec_id=spec.spec_id,
        rule=spec.rule,
        verdict=Verdict.PASS if passed else Verdict.REJECT,
        claim="oscillator",
        claimed_period=p,
        observed_period=observed_period,
        claimed_displacement=(0, 0),
        observed_displacement=(0, 0) if observed_period is not None else None,
        residual_cell_count=residual,
        rotor_cell_count=len(rotor),
        stator_cell_count=len(stator),
        field_size=(candidate.width, candidate.height),
        margin=candidate.width + candidate.height,
        t_settle=0,
        reference_sim_version_hash=reference_sim_version_hash(),
        producer_engine_version_hash=producer_engine_version_hash,
        notes="; ".join(notes),
    )
    return record.signed()


def _verify_stilllife(
    candidate: Pattern, spec: StillLife, producer_engine_version_hash: str | None
) -> VerificationRecord:
    nxt = reference.step(candidate, 1)
    residual = len(nxt.cells ^ candidate.cells)
    stable = residual == 0 and not candidate.is_empty

    notes = []
    if candidate.is_empty:
        notes.append("empty candidate")
    if residual != 0:
        notes.append(f"not stable: {residual} cells change after one generation")

    spec_met = stable
    if spec.bbox_max is not None and not candidate.is_empty:
        w_max, h_max = spec.bbox_max
        if candidate.width > w_max or candidate.height > h_max:
            spec_met = False
            notes.append(f"bbox {(candidate.width, candidate.height)} exceeds bbox_max {spec.bbox_max}")
    if spec.population_range is not None:
        lo, hi = spec.population_range
        if not (lo <= candidate.population <= hi):  # post-hoc filter
            spec_met = False
            notes.append(f"population {candidate.population} outside range {spec.population_range}")

    record = VerificationRecord(
        spec_id=spec.spec_id,
        rule=spec.rule,
        verdict=Verdict.PASS if spec_met else Verdict.REJECT,
        claim="still_life",
        claimed_period=1,
        observed_period=1 if stable else None,
        claimed_displacement=(0, 0),
        observed_displacement=(0, 0) if stable else None,
        residual_cell_count=residual,
        field_size=(candidate.width, candidate.height),
        margin=candidate.width + candidate.height,
        t_settle=0,
        reference_sim_version_hash=reference_sim_version_hash(),
        producer_engine_version_hash=producer_engine_version_hash,
        notes="; ".join(notes),
    )
    return record.signed()


def verify_nonexistence(
    witness: OrphanWitness | None,
    rule: str,
    spec_id: str = "",
    producer_engine_version_hash: str | None = None,
) -> VerificationRecord:
    """Verify a Garden-of-Eden / 'no such object' claim (SPEC §5.2).

    A non-existence verdict is granted ONLY with an orphan witness carrying an
    exhaustive no-preimage proof and a forced-dead border of thickness >= 4. A missing
    witness or a single small-box UNSAT is REJECTED — never silently treated as proof.
    """
    notes = []
    if witness is None:
        notes.append("no orphan witness — cannot establish non-existence from absence of a find")
        established = False
    else:
        established = (
            witness.no_preimage_proof
            and witness.padding_thickness >= GOE_MIN_PADDING
            and not witness.orphan.is_empty
        )
        if not witness.no_preimage_proof:
            notes.append("no exhaustive no-preimage proof (small-box UNSAT is insufficient)")
        if witness.padding_thickness < GOE_MIN_PADDING:
            notes.append(
                f"padding thickness {witness.padding_thickness} < required {GOE_MIN_PADDING}"
            )
        if witness.orphan.is_empty:
            notes.append("empty orphan")

    record = VerificationRecord(
        spec_id=spec_id,
        rule=rule,
        verdict=Verdict.PASS if established else Verdict.REJECT,
        claim="nonexistence",
        reference_sim_version_hash=reference_sim_version_hash(),
        producer_engine_version_hash=producer_engine_version_hash,
        notes="; ".join(notes) or "orphan witness validated",
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
    if isinstance(spec, Oscillator):
        return _verify_oscillator(candidate, spec, producer_engine_version_hash)
    if isinstance(spec, StillLife):
        return _verify_stilllife(candidate, spec, producer_engine_version_hash)
    raise NotImplementedError(f"verification not implemented for spec kind {spec.kind!r}")
