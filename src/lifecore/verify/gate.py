"""Acceptance gate (Task 3.4, SPEC §5.4) — the ONLY path to store.accept().

``ACCEPTED ⇔ verifier.verdict == PASS ∧ novelty.status == NOVEL``. The gate is a pure
function with NO setters: it cannot widen a spec, override a verdict, or reinterpret an
UNCERTAIN novelty as NOVEL. The decision it returns is frozen.
"""

from __future__ import annotations

from dataclasses import dataclass

from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.verify.records import Verdict, VerificationRecord


@dataclass(frozen=True)
class AcceptanceDecision:
    """Frozen record of an accept/reject decision and why."""

    accepted: bool
    verification: VerificationRecord
    novelty: NoveltyResult
    reason: str


def accept(verification: VerificationRecord, novelty: NoveltyResult) -> AcceptanceDecision:
    """Combine an independent verification with a novelty verdict. No mutation, no override."""
    verified = verification.verdict is Verdict.PASS
    novel = novelty.status is NoveltyStatus.NOVEL
    accepted = verified and novel

    if accepted:
        reason = "accepted: verified PASS and novelty NOVEL"
    elif not verified:
        reason = f"rejected: verification verdict {verification.verdict.value}"
    else:
        reason = f"rejected: novelty status {novelty.status.value} (only NOVEL is accepted)"

    return AcceptanceDecision(
        accepted=accepted, verification=verification, novelty=novelty, reason=reason
    )
