"""Typed, mechanism-faithful target specs (Task 2.1 base; 2.2/2.3 extend).

All specs are frozen pydantic models: hashed to a ``spec_id`` and immutable from the
agent side (SPEC §1.5, §4.1). The base here carries the common fields + machinery
(deterministic hashing, freeze, a kind→class registry for YAML reconstruction);
concrete object types (Spaceship, Oscillator, StillLife, stubs) are added in 2.2/2.3.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

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


# kind value -> concrete TargetSpec subclass, for YAML reconstruction.
_REGISTRY: dict[str, type[TargetSpec]] = {}


class TargetSpec(BaseModel):
    """Base target specification. Frozen + value-equal; identity is :attr:`spec_id`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: str = "B3/S23"
    kind: SpecKind
    notes: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Register concrete subclasses by the default value of their `kind` field.
        field = cls.model_fields.get("kind")
        if field is not None and field.default is not None:
            default = field.default
            value = default.value if isinstance(default, SpecKind) else str(default)
            _REGISTRY[value] = cls

    def canonical_payload(self) -> dict[str, Any]:
        """JSON-able dict used for hashing and serialization (enums→values, tuples→lists)."""
        return self.model_dump(mode="json")

    @property
    def spec_id(self) -> str:
        return spec_id_for(self.canonical_payload())

    def freeze(self) -> TargetSpec:
        """Return an immutable copy (models are already frozen; this is explicit intent)."""
        return self.model_copy(deep=True)


def spec_class_for(kind: str | SpecKind) -> type[TargetSpec]:
    """Look up the concrete spec class registered for ``kind``."""
    value = kind.value if isinstance(kind, SpecKind) else str(kind)
    try:
        return _REGISTRY[value]
    except KeyError as exc:
        raise KeyError(f"no TargetSpec class registered for kind {value!r}") from exc
