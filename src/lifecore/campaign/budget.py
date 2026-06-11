"""First-class budget accounting with hard stops (Task 7.2, SPEC §8).

A campaign's spend (dollars, tokens, engine CPU, replans) is tracked by a mutable
:class:`BudgetLedger` bounded by immutable :class:`BudgetLimits`. Every charge is
*atomic*: it records the spend into the running totals and THEN raises
:class:`BudgetExceeded` if any corresponding limit is now exceeded. The ledger
therefore always reflects the overspend that tripped the hard stop, which is what
gets written into provenance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetLimits:
    """Immutable hard caps for a campaign (SPEC §8)."""

    max_usd: float = 1.0
    max_tokens: int = 1_000_000
    max_engine_cpu_seconds: float = 600.0
    max_replans: int = 10


class BudgetExceeded(Exception):
    """Raised the moment a charge pushes a running total past its limit."""


class BudgetLedger:
    """Mutable running totals bounded by :class:`BudgetLimits`, with hard stops."""

    def __init__(self, limits: BudgetLimits) -> None:
        self.limits = limits
        self.spent_usd: float = 0.0
        self.spent_tokens: int = 0
        self.engine_cpu_seconds: float = 0.0
        self.replans: int = 0

    def charge_tokens(self, tokens: int, usd: float) -> None:
        """Record token + dollar spend, then hard-stop if either cap is exceeded."""
        self.spent_tokens += tokens
        self.spent_usd += usd
        if self.spent_tokens > self.limits.max_tokens:
            raise BudgetExceeded(
                f"tokens {self.spent_tokens} exceed limit {self.limits.max_tokens}"
            )
        if self.spent_usd > self.limits.max_usd:
            raise BudgetExceeded(f"usd {self.spent_usd} exceeds limit {self.limits.max_usd}")

    def charge_engine_cpu(self, seconds: float) -> None:
        """Record engine CPU spend, then hard-stop if the cap is exceeded."""
        self.engine_cpu_seconds += seconds
        if self.engine_cpu_seconds > self.limits.max_engine_cpu_seconds:
            raise BudgetExceeded(
                f"engine cpu {self.engine_cpu_seconds}s exceeds limit "
                f"{self.limits.max_engine_cpu_seconds}s"
            )

    def charge_replan(self) -> None:
        """Record a replan, then hard-stop if the replan cap is exceeded."""
        self.replans += 1
        if self.replans > self.limits.max_replans:
            raise BudgetExceeded(f"replans {self.replans} exceed limit {self.limits.max_replans}")

    def remaining(self) -> dict[str, float | int]:
        """Headroom left under each limit (clamped at zero is NOT applied — may go negative)."""
        return {
            "usd": self.limits.max_usd - self.spent_usd,
            "tokens": self.limits.max_tokens - self.spent_tokens,
            "engine_cpu_seconds": self.limits.max_engine_cpu_seconds - self.engine_cpu_seconds,
            "replans": self.limits.max_replans - self.replans,
        }

    def as_dict(self) -> dict[str, float | int]:
        """Provenance snapshot of running totals."""
        return {
            "spent_usd": self.spent_usd,
            "spent_tokens": self.spent_tokens,
            "engine_cpu_seconds": self.engine_cpu_seconds,
            "replans": self.replans,
        }
