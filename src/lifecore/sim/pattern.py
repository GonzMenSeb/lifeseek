"""Immutable Pattern model — the shared currency of lifecore (Task 1.1 contract).

A ``Pattern`` is a rule-tagged, immutable set of live cells on the integer lattice.
It carries *no* simulation logic: producers (lifelib) and the reference verifier
(numpy) both speak Pattern, but neither lives here. Frozen + value-hashed so it can
be used as a dict/set key and safely shared across the deterministic pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Cell = tuple[int, int]
BBox = tuple[int, int, int, int]  # (xmin, ymin, xmax, ymax)

DEFAULT_RULE = "B3/S23"


@dataclass(frozen=True, slots=True)
class Pattern:
    """Immutable live-cell set under a named rule.

    ``cells`` are ``(x, y)`` integer coordinates (x = column, y = row, y grows down,
    matching RLE). Equality and hashing are value-based over ``(cells, rule)``.
    """

    cells: frozenset[Cell]
    rule: str = field(default=DEFAULT_RULE)

    def __post_init__(self) -> None:
        # Accept any iterable of pairs but always store a frozenset of int tuples.
        if not isinstance(self.cells, frozenset):
            object.__setattr__(self, "cells", frozenset((int(x), int(y)) for x, y in self.cells))

    # --- size / extent -------------------------------------------------------
    @property
    def population(self) -> int:
        return len(self.cells)

    @property
    def is_empty(self) -> bool:
        return not self.cells

    @property
    def bbox(self) -> BBox:
        """Inclusive bounding box. Empty pattern -> (0, 0, -1, -1) so width/height == 0."""
        if not self.cells:
            return (0, 0, -1, -1)
        xs = [c[0] for c in self.cells]
        ys = [c[1] for c in self.cells]
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def width(self) -> int:
        xmin, _, xmax, _ = self.bbox
        return xmax - xmin + 1

    @property
    def height(self) -> int:
        _, ymin, _, ymax = self.bbox
        return ymax - ymin + 1

    # --- transforms (return new Patterns; never mutate) ----------------------
    def translate(self, dx: int, dy: int) -> Pattern:
        if dx == 0 and dy == 0:
            return self
        return Pattern(frozenset((x + dx, y + dy) for x, y in self.cells), self.rule)

    def normalize(self) -> Pattern:
        """Translate so the bounding box min corner sits at the origin (0, 0)."""
        if not self.cells:
            return self
        xmin, ymin, _, _ = self.bbox
        return self.translate(-xmin, -ymin)

    def with_rule(self, rule: str) -> Pattern:
        return self if rule == self.rule else Pattern(self.cells, rule)
