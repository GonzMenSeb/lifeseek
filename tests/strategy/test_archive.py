from __future__ import annotations

import random
from dataclasses import FrozenInstanceError

import pytest

from lifecore.strategy.archive import (
    StrategyArchive,
    StrategyNode,
    StrategyOutcome,
    meta_utility,
)


def test_archive_is_append_only() -> None:
    archive = StrategyArchive()
    n0 = archive.add(None, {"engine": "qfind"}, StrategyOutcome(verified_novel=1, budget_spent=2.0))
    n1 = archive.add(n0.node_id, {"engine": "lls"}, StrategyOutcome(verified_novel=0, budget_spent=1.0))

    # nodes() is a read-only tuple snapshot
    nodes = archive.nodes()
    assert isinstance(nodes, tuple)
    assert nodes == (n0, n1)

    # no public mutator/remover on the archive
    assert not hasattr(archive, "remove")
    assert not hasattr(archive, "set")
    assert not hasattr(archive, "clear")

    # returned nodes are frozen
    with pytest.raises(FrozenInstanceError):
        n0.node_id = 99  # type: ignore[misc]


def test_node_ids_increment() -> None:
    archive = StrategyArchive()
    ids = [
        archive.add(None, {}, StrategyOutcome(verified_novel=0, budget_spent=1.0)).node_id
        for _ in range(5)
    ]
    assert ids == [0, 1, 2, 3, 4]


def test_unsat_on_impossible_is_credited() -> None:
    budget = 7.0
    credited = StrategyOutcome(verified_novel=0, budget_spent=budget, correct_unsat=True)
    thrashing = StrategyOutcome(verified_novel=0, budget_spent=budget, correct_unsat=False)
    assert meta_utility(thrashing) == 0.0
    assert meta_utility(credited) > 0.0
    assert meta_utility(credited) > meta_utility(thrashing)


def test_select_parent_prefers_high_utility_low_children() -> None:
    archive = StrategyArchive()
    # high-utility, childless node
    good = archive.add(None, {"k": "good"}, StrategyOutcome(verified_novel=10, budget_spent=1.0))
    # low-utility node, give it many children to suppress it
    bad = archive.add(None, {"k": "bad"}, StrategyOutcome(verified_novel=0, budget_spent=100.0))
    for _ in range(20):
        archive.add(bad.node_id, {}, StrategyOutcome(verified_novel=0, budget_spent=100.0))

    rng = random.Random(1234)
    counts = {good.node_id: 0, bad.node_id: 0}
    for _ in range(2000):
        chosen = archive.select_parent(rng)
        assert chosen is not None
        if chosen.node_id in counts:
            counts[chosen.node_id] += 1
    assert counts[good.node_id] > counts[bad.node_id]


def test_select_parent_empty_returns_none() -> None:
    archive = StrategyArchive()
    assert archive.select_parent(random.Random(0)) is None


def test_strategynode_is_frozen() -> None:
    node = StrategyNode(
        node_id=0,
        parent_id=None,
        descriptor={},
        outcome=StrategyOutcome(verified_novel=0, budget_spent=1.0),
    )
    with pytest.raises(FrozenInstanceError):
        node.parent_id = 5  # type: ignore[misc]
