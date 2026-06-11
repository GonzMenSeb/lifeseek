"""Typed, mechanism-faithful target specs (Task 2.1 base; 2.2/2.3 extend).

All specs are frozen pydantic models: hashed to a ``spec_id`` and immutable from the
agent side (SPEC §1.5, §4.1). The base here carries the common fields + machinery
(deterministic hashing, freeze, a kind→class registry for YAML reconstruction);
concrete object types (Spaceship, Oscillator, StillLife, stubs) are added in 2.2/2.3.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from lifecore.targetspec.hashing import spec_id_for


class SpecKind(StrEnum):
    SPACESHIP = "spaceship"
    OSCILLATOR = "oscillator"
    STILL_LIFE = "still_life"
    GUN = "gun"
    PUFFER = "puffer"
    RAKE = "rake"
    EATER = "eater"


class SymmetryClass(StrEnum):
    ASYMMETRIC = "asymmetric"
    BILATERAL_EVEN = "bilateral_even"
    BILATERAL_ODD = "bilateral_odd"
    GLIDE_REFLECT = "glide_reflect"


class SlopeClass(StrEnum):
    ORTHOGONAL = "orthogonal"
    DIAGONAL = "diagonal"
    OBLIQUE = "oblique"


class TargetSpec(BaseModel):
    """Base target specification. Frozen + value-equal; identity is :attr:`spec_id`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: str = "B3/S23"
    kind: SpecKind
    notes: str = ""

    def canonical_payload(self) -> dict[str, Any]:
        """JSON-able dict used for hashing and serialization (enums→values, tuples→lists)."""
        return self.model_dump(mode="json")

    @property
    def spec_id(self) -> str:
        return spec_id_for(self.canonical_payload())

    def freeze(self) -> TargetSpec:
        """Return an immutable copy (models are already frozen; this is explicit intent)."""
        return self.model_copy(deep=True)


def _iter_subclasses(cls: type[TargetSpec]) -> Iterator[type[TargetSpec]]:
    for sub in cls.__subclasses__():
        yield sub
        yield from _iter_subclasses(sub)


def spec_class_for(kind: str | SpecKind) -> type[TargetSpec]:
    """Find the concrete TargetSpec subclass whose default ``kind`` matches ``kind``.

    Resolved lazily over the subclass tree (definition order), so library types take
    precedence over test doubles that may share a kind.
    """
    value = kind.value if isinstance(kind, SpecKind) else str(kind)
    for sub in _iter_subclasses(TargetSpec):
        field = sub.model_fields.get("kind")
        if field is None or field.default is None:
            continue
        default = field.default
        sub_value = default.value if isinstance(default, SpecKind) else str(default)
        if sub_value == value:
            return sub
    raise KeyError(f"no TargetSpec class registered for kind {value!r}")


def _speed_fraction(distance: int, period: int) -> str:
    """Format a sub-lightspeed fraction of c, e.g. (2, 4) -> 'c/2', (3, 4) -> '3c/4'."""
    from math import gcd

    g = gcd(distance, period)
    num, den = distance // g, period // g
    return "c" if den == 1 else (f"c/{den}" if num == 1 else f"{num}c/{den}")


class Spaceship(TargetSpec):
    """A translating periodic pattern (SPEC §4.1).

    ``population_range`` and ``bbox_max`` are **post-hoc filters**, never engine
    inputs — engines ignore them; they only gate acceptance after a candidate is
    found. ``search_width`` is the dominant cost lever and the real engine input.
    """

    kind: SpecKind = SpecKind.SPACESHIP
    displacement: tuple[int, int]
    period: int
    symmetry_class: SymmetryClass
    search_width: tuple[int, int]  # (w_min, w_max)
    population_range: tuple[int, int] | None = None  # post-hoc filter
    bbox_max: tuple[int, int] | None = None  # post-hoc filter

    @model_validator(mode="after")
    def _validate(self) -> Spaceship:
        dx, dy = abs(self.displacement[0]), abs(self.displacement[1])
        if self.period < 1:
            raise ValueError("period must be >= 1")
        if dx == 0 and dy == 0:
            raise ValueError("displacement (0,0) is an oscillator, not a spaceship")
        if max(dx, dy) > self.period:
            raise ValueError(
                f"displacement {self.displacement} over period {self.period} exceeds lightspeed"
            )
        w_min, w_max = self.search_width
        if w_min < 1:
            raise ValueError("search_width minimum must be >= 1")
        if w_min > w_max:
            raise ValueError(f"search_width inverted: w_min={w_min} > w_max={w_max}")
        return self

    @property
    def slope(self) -> SlopeClass:
        dx, dy = abs(self.displacement[0]), abs(self.displacement[1])
        if dx == 0 or dy == 0:
            return SlopeClass.ORTHOGONAL
        if dx == dy:
            return SlopeClass.DIAGONAL
        return SlopeClass.OBLIQUE

    @property
    def velocity(self) -> str:
        dx, dy = abs(self.displacement[0]), abs(self.displacement[1])
        slope = self.slope
        if slope is SlopeClass.OBLIQUE:
            return f"({dx},{dy})c/{self.period} oblique"
        return f"{_speed_fraction(max(dx, dy), self.period)} {slope.value}"

    def engine_params(self) -> dict[str, Any]:
        """ONLY the mechanism inputs an engine consumes — never the post-hoc filters."""
        return {
            "rule": self.rule,
            "displacement": self.displacement,
            "period": self.period,
            "symmetry_class": self.symmetry_class.value,
            "search_width": self.search_width,
            "slope": self.slope.value,
        }
