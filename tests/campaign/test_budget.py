"""Tests for the budget ledger with hard stops (Task 7.2, SPEC §8)."""

from __future__ import annotations

import pytest

from lifecore.campaign.budget import BudgetExceeded, BudgetLedger, BudgetLimits


def test_charges_accumulate() -> None:
    ledger = BudgetLedger(BudgetLimits(max_usd=10.0, max_tokens=1000, max_engine_cpu_seconds=100.0))
    ledger.charge_tokens(100, 0.5)
    ledger.charge_tokens(200, 0.25)
    ledger.charge_engine_cpu(10.0)
    ledger.charge_engine_cpu(5.0)
    ledger.charge_replan()

    assert ledger.spent_tokens == 300
    assert ledger.spent_usd == pytest.approx(0.75)
    assert ledger.engine_cpu_seconds == pytest.approx(15.0)
    assert ledger.replans == 1


def test_budget_hard_stop_raises_tokens() -> None:
    ledger = BudgetLedger(BudgetLimits(max_tokens=500, max_usd=1000.0))
    ledger.charge_tokens(400, 0.0)
    with pytest.raises(BudgetExceeded):
        ledger.charge_tokens(200, 0.0)
    # Atomic: the overspend that tripped the stop is recorded.
    assert ledger.spent_tokens == 600


def test_budget_hard_stop_raises_usd() -> None:
    ledger = BudgetLedger(BudgetLimits(max_usd=1.0, max_tokens=10**9))
    with pytest.raises(BudgetExceeded):
        ledger.charge_tokens(1, 1.5)
    assert ledger.spent_usd == pytest.approx(1.5)


def test_budget_hard_stop_raises_engine_cpu() -> None:
    ledger = BudgetLedger(BudgetLimits(max_engine_cpu_seconds=30.0))
    ledger.charge_engine_cpu(20.0)
    with pytest.raises(BudgetExceeded):
        ledger.charge_engine_cpu(15.0)
    assert ledger.engine_cpu_seconds == pytest.approx(35.0)


def test_budget_hard_stop_raises_replans() -> None:
    ledger = BudgetLedger(BudgetLimits(max_replans=2))
    ledger.charge_replan()
    ledger.charge_replan()
    with pytest.raises(BudgetExceeded):
        ledger.charge_replan()
    assert ledger.replans == 3


def test_remaining_reports_headroom() -> None:
    ledger = BudgetLedger(
        BudgetLimits(max_usd=2.0, max_tokens=1000, max_engine_cpu_seconds=100.0, max_replans=5)
    )
    ledger.charge_tokens(250, 0.5)
    ledger.charge_engine_cpu(40.0)
    ledger.charge_replan()

    rem = ledger.remaining()
    assert rem["usd"] == pytest.approx(1.5)
    assert rem["tokens"] == 750
    assert rem["engine_cpu_seconds"] == pytest.approx(60.0)
    assert rem["replans"] == 4

    snap = ledger.as_dict()
    assert snap["spent_tokens"] == 250
    assert snap["replans"] == 1
