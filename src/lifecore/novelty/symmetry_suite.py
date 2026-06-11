"""Symmetry soundness suite (Task 4.4, SPEC §6.1 — release blocker).

Every catalog object, under all 8 dihedral images x several phases x random
translations, MUST canonicalize to a single apgcode and be flagged KNOWN. If it does
not, the canonicalizer is unsound and novelty cannot be trusted. This module provides
the orbit generator and soundness checks; the release-blocking test exercises them.
"""

from __future__ import annotations

import random
from collections.abc import Iterator

from lifecore.novelty import canonical
from lifecore.novelty.canonical import dihedral_images
from lifecore.sim import reference
from lifecore.sim.pattern import Pattern


def _random_offsets(seed: int, count: int, span: int = 50) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    return [(rng.randint(-span, span), rng.randint(-span, span)) for _ in range(count)]


def symmetry_variants(
    pattern: Pattern,
    *,
    n_phases: int = 4,
    n_translations: int = 4,
    seed: int = 0,
) -> Iterator[Pattern]:
    """Yield D8 images of each of the first ``n_phases`` phases, each randomly translated."""
    offsets = _random_offsets(seed, n_translations)
    for i in range(n_phases):
        phase = reference.step(pattern, i) if i else pattern
        for image in dihedral_images(phase):
            for dx, dy in offsets:
                yield image.translate(dx, dy)


def apgcodes_for_orbit(pattern: Pattern, **kwargs: int) -> set[str]:
    """The set of apgcodes produced over the full symmetry orbit (should be a singleton)."""
    return {canonical.apgcode(v) for v in symmetry_variants(pattern, **kwargs)}


def is_symmetry_sound(pattern: Pattern, **kwargs: int) -> bool:
    """True iff every image in the symmetry orbit canonicalizes to the same apgcode."""
    return len(apgcodes_for_orbit(pattern, **kwargs)) == 1
