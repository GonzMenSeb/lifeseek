"""Tests for the reproducible recipe object (Task 5.2, SPEC §9)."""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from lifecore.store.recipe import (
    Recipe,
    current_canonicalizer_version,
    current_reference_sim_version,
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _recipe(**overrides: object) -> Recipe:
    base: dict[str, object] = {
        "engine": "rlifesrc",
        "engine_version": "0.6.0",
        "build_flags": "--release",
        "config": {"width": 10, "height": 8},
        "seed": 42,
        "budget": {"wall_seconds": 120},
        "reference_sim_version": "a" * 64,
        "canonicalizer_version": "b" * 64,
        "catagolue_snapshot_hash": "c" * 64,
        "container_image_digest": "sha256:" + "d" * 64,
        "spec_id": "e" * 64,
    }
    base.update(overrides)
    return Recipe(**base)  # type: ignore[arg-type]


def test_recipe_id_stable_and_order_independent() -> None:
    r1 = _recipe(config={"width": 10, "height": 8}, budget={"a": 1, "b": 2})
    r2 = _recipe(config={"height": 8, "width": 10}, budget={"b": 2, "a": 1})
    assert r1.recipe_id == r2.recipe_id
    assert _HEX64.match(r1.recipe_id)
    # a changed field changes the id
    assert _recipe(seed=43).recipe_id != r1.recipe_id


def test_recipe_roundtrips_through_json() -> None:
    r = _recipe(notes="first run")
    data = r.model_dump(mode="json")
    restored = Recipe(**data)
    assert restored == r
    assert restored.recipe_id == r.recipe_id


def test_recipe_is_frozen() -> None:
    r = _recipe()
    with pytest.raises(ValidationError):
        r.seed = 99
    with pytest.raises(ValidationError):
        Recipe(**{**r.model_dump(), "unexpected": 1})  # extra forbidden


def test_version_hashes_are_hex64() -> None:
    ref = current_reference_sim_version()
    canon = current_canonicalizer_version()
    assert _HEX64.match(ref)
    assert _HEX64.match(canon)
    assert ref != canon  # distinct source files
