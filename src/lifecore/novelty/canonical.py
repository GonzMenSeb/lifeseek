"""Canonicalization (Task 4.1, SPEC §6.1).

Two paths, deliberately independent:

* :func:`apgcode` — the producer-backend canonical form (lifelib). Fast, authoritative
  against Catagolue, but a single code path.
* :func:`independent_canonical` — a lifelib-FREE canonical signature computed on the
  reference simulator over the object's full orbit, invariant under translation, the 8
  dihedral images, and phase. Used to cross-check accepted discoveries so a bug in the
  producer's canonicalizer cannot, by itself, let a non-novel object through (SPEC §6.1).
"""

from __future__ import annotations

from collections.abc import Iterator

from lifecore.sim import reference
from lifecore.sim.pattern import Cell, Pattern

# The 8 dihedral (D4) transforms on integer cells.
_D8: tuple[tuple[int, int, int, int], ...] = (
    (1, 0, 0, 1),  # identity
    (0, -1, 1, 0),  # rot90
    (-1, 0, 0, -1),  # rot180
    (0, 1, -1, 0),  # rot270
    (-1, 0, 0, 1),  # flip x
    (1, 0, 0, -1),  # flip y
    (0, 1, 1, 0),  # transpose
    (0, -1, -1, 0),  # anti-transpose
)


def _apply(t: tuple[int, int, int, int], cells: frozenset[Cell]) -> frozenset[Cell]:
    a, b, c, d = t
    return frozenset((a * x + b * y, c * x + d * y) for x, y in cells)


def dihedral_images(pattern: Pattern) -> Iterator[Pattern]:
    """Yield the 8 dihedral images of ``pattern`` (same rule)."""
    for t in _D8:
        yield Pattern(_apply(t, pattern.cells), pattern.rule)


def _serialize(cells: frozenset[Cell]) -> str:
    return ";".join(f"{x},{y}" for x, y in sorted(cells))


def _orbit_period(pattern: Pattern, cap: int) -> int:
    """Minimal n with step(pattern, n) a pure translation of pattern (covers ship/osc/still)."""
    if pattern.is_empty:
        return 1
    shape = pattern.normalize().cells
    for n in range(1, cap + 1):
        if reference.step(pattern, n).normalize().cells == shape:
            return n
    return 1  # not periodic within cap: canonicalize the single given phase


def independent_canonical(pattern: Pattern, cap: int = 64) -> str:
    """Lifelib-free canonical key: lexicographically minimal serialization over the
    orbit phases x 8 dihedral images x translation (normalized to the origin)."""
    period = _orbit_period(pattern, cap)
    best: str | None = None
    for i in range(period):
        phase = reference.step(pattern, i) if i else pattern
        for t in _D8:
            normalized = Pattern(_apply(t, phase.cells)).normalize().cells
            key = _serialize(normalized)
            if best is None or key < best:
                best = key
    return best or ""


def apgcode(pattern: Pattern) -> str:
    """Producer-backend apgcode (lifelib). Raises ImportError without the lifelib extra."""
    from lifecore.sim import lifelib_engine

    return lifelib_engine.apgcode(pattern)
