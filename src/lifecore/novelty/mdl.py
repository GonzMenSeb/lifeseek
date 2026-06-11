"""MDL / minimality tier (Task 4.3, SPEC §6.3).

The fail-closed novelty oracle's *minimality* tier: it rejects a
**derivative-of-known** pattern — one that is merely a known object plus a
*separable inert* component (a juxtaposition), rather than an irreducible novel
mechanism. This tier is deliberately lifelib-FREE: it identifies components via
:func:`independent_canonical`, so its tests never need the lifelib extra.

It only *rejects derivatives*; confirming true novelty is the wider oracle's job.
"""

from __future__ import annotations

from collections.abc import Callable

from lifecore.novelty.canonical import independent_canonical
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Cell, Pattern

# 8-connected (king-move) neighbour offsets.
_NEIGHBOURS: tuple[Cell, ...] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


def connected_components(pattern: Pattern) -> list[Pattern]:
    """Split live cells into maximal 8-connected components (king-move adjacency).

    Each component is a :class:`Pattern` with the SAME rule and cells kept at their
    ORIGINAL absolute coordinates (not normalized). Components are returned sorted by
    their ``(xmin, ymin)`` for determinism.
    """
    remaining: set[Cell] = set(pattern.cells)
    components: list[Pattern] = []
    while remaining:
        seed = remaining.pop()
        component: set[Cell] = {seed}
        stack: list[Cell] = [seed]
        while stack:
            x, y = stack.pop()
            for dx, dy in _NEIGHBOURS:
                neighbour = (x + dx, y + dy)
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    component.add(neighbour)
                    stack.append(neighbour)
        components.append(Pattern(frozenset(component), pattern.rule))
    components.sort(key=lambda c: (c.bbox[0], c.bbox[1]))
    return components


def description_length(pattern: Pattern) -> int:
    """Cheap MDL proxy: population + number of connected components."""
    return pattern.population + len(connected_components(pattern))


def classify(
    pattern: Pattern,
    known_keys: set[str],
    *,
    identity: Callable[[Pattern], str] = independent_canonical,
) -> NoveltyResult:
    """Reject derivative-of-known patterns.

    Returns ``DERIVATIVE`` iff the pattern decomposes into >= 2 components and at least
    one component's ``identity`` is in ``known_keys`` (a separable, already-known
    sub-object — a juxtaposition, not an irreducible novel mechanism). Otherwise returns
    ``NOVEL``, meaning only that this tier found no derivative-of-known decomposition.
    """
    components = connected_components(pattern)
    if len(components) >= 2:
        known_components = [c for c in components if identity(c) in known_keys]
        if known_components:
            nearest = max(known_components, key=lambda c: c.population)
            mdl_delta = description_length(pattern) - description_length(nearest)
            return NoveltyResult(
                status=NoveltyStatus.DERIVATIVE,
                nearest_known=identity(nearest),
                mdl_delta=mdl_delta,
                notes=(
                    f"derivative: {len(components)} separable components, "
                    f"{len(known_components)} known; reducible to a known sub-object"
                ),
            )
    return NoveltyResult(
        status=NoveltyStatus.NOVEL,
        notes="no derivative-of-known decomposition (minimality tier)",
    )
