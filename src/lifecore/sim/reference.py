"""Independent NumPy reference simulator — the verification trust path (Task 1.2).

This module is the *only* simulator the verifier is allowed to use (SPEC §1.2,
§5.1). It MUST NOT import the producer backend (lifelib): verification by an
independent code path is the whole point. The implementation is a deliberately
simple, vectorized neighbour-count evolution with an auto-expanding bounded grid,
so it can never silently clip a growing pattern.
"""

from __future__ import annotations

import re

import numpy as np

from lifecore.sim.pattern import Pattern

_RULE_RE = re.compile(r"^B(?P<birth>\d*)/S(?P<survive>\d*)$", re.IGNORECASE)


def parse_rule(rule: str) -> tuple[frozenset[int], frozenset[int]]:
    """Parse a ``Bxx/Sxx`` rulestring into (birth_counts, survival_counts)."""
    match = _RULE_RE.match(rule.strip())
    if match is None:
        raise ValueError(f"unsupported rule string: {rule!r} (expected 'Bxx/Sxx')")
    birth = frozenset(int(d) for d in match.group("birth"))
    survive = frozenset(int(d) for d in match.group("survive"))
    return birth, survive


def _neighbour_counts(grid: np.ndarray) -> np.ndarray:
    """8-neighbour live counts for every cell (grid is zero-padded by construction)."""
    counts = np.zeros(grid.shape, dtype=np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            counts += np.roll(np.roll(grid, dy, axis=0), dx, axis=1)
    return counts


def step(pattern: Pattern, n: int) -> Pattern:
    """Evolve ``pattern`` exactly ``n`` generations under its rule.

    The grid is padded by ``n`` cells on every side (plus a 1-cell guard) so growth
    of at most one cell per generation can never reach the border — i.e. no clipping.
    Absolute cell coordinates are preserved (no implicit normalization).
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0 or pattern.is_empty:
        return pattern

    birth, survive = parse_rule(pattern.rule)

    xmin, ymin, xmax, ymax = pattern.bbox
    pad = n + 1
    width = (xmax - xmin + 1) + 2 * pad
    height = (ymax - ymin + 1) + 2 * pad
    # offset mapping absolute (x, y) -> grid index: col = x - xmin + pad, row = y - ymin + pad
    grid = np.zeros((height, width), dtype=np.uint8)
    for x, y in pattern.cells:
        grid[y - ymin + pad, x - xmin + pad] = 1

    birth_arr = np.zeros(9, dtype=bool)
    survive_arr = np.zeros(9, dtype=bool)
    for b in birth:
        birth_arr[b] = True
    for s in survive:
        survive_arr[s] = True

    for _ in range(n):
        counts = _neighbour_counts(grid)
        alive = grid.astype(bool)
        next_grid = np.where(alive, survive_arr[counts], birth_arr[counts])
        grid = next_grid.astype(np.uint8)

    rows, cols = np.nonzero(grid)
    cells = frozenset(
        (int(c) - pad + xmin, int(r) - pad + ymin) for r, c in zip(rows, cols, strict=True)
    )
    return Pattern(cells, pattern.rule)
