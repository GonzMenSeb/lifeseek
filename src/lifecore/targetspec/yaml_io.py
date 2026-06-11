"""YAML serialization for target specs — the re-aim knob (Task 2.1, SPEC §4.1).

Editing a spec's YAML and re-running is how a campaign is re-aimed with zero code
changes. ``to_yaml`` emits the canonical payload; ``from_yaml`` reconstructs the
concrete spec class via the ``kind`` discriminator (or an explicit class override).
"""

from __future__ import annotations

from typing import Any

import yaml

from lifecore.targetspec.models import TargetSpec, spec_class_for


def to_yaml(spec: TargetSpec) -> str:
    """Serialize ``spec`` to canonical YAML (sorted keys, block style)."""
    return yaml.safe_dump(spec.canonical_payload(), sort_keys=True, default_flow_style=False)


def from_yaml(text: str, cls: type[TargetSpec] | None = None) -> TargetSpec:
    """Reconstruct a spec from YAML.

    The concrete class is ``cls`` if given, else looked up from the ``kind`` field.
    """
    data: dict[str, Any] = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("spec YAML must be a mapping")
    target_cls = cls if cls is not None else spec_class_for(data["kind"])
    return target_cls(**data)
