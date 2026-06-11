"""Signed verification records (Task 3.1, SPEC §5.3).

A ``VerificationRecord`` is the deterministic, tamper-evident output of the gate: it
captures exactly what was claimed, what was observed on the independent reference
simulator, and a content ``signature`` (sha256 over the canonical payload) so any
later replay can prove bitwise identity. No mutation API.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from lifecore.targetspec.hashing import canonical_json


class Verdict(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"


def reference_sim_version_hash() -> str:
    """SHA-256 of the reference simulator source — pins the verification code path."""
    from lifecore.sim import reference

    src = Path(reference.__file__ or "")
    return hashlib.sha256(src.read_bytes()).hexdigest()


class VerificationRecord(BaseModel):
    """Immutable, signed record of one verification (SPEC §5.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    spec_id: str
    rule: str
    verdict: Verdict
    claimed_period: int | None = None
    observed_period: int | None = None
    claimed_displacement: tuple[int, int] | None = None
    observed_displacement: tuple[int, int] | None = None
    residual_cell_count: int = 0
    field_size: tuple[int, int] | None = None
    margin: int = 0
    t_settle: int = 0
    reference_sim_version_hash: str = ""
    producer_engine_version_hash: str | None = None
    notes: str = ""
    signature: str = ""

    def _payload_for_signature(self) -> dict[str, object]:
        data = self.model_dump(mode="json")
        data.pop("signature", None)
        return data

    def signed(self) -> VerificationRecord:
        """Return a copy with ``signature`` set to the content hash of all other fields."""
        sig = hashlib.sha256(canonical_json(self._payload_for_signature()).encode()).hexdigest()
        return self.model_copy(update={"signature": sig})

    def signature_valid(self) -> bool:
        expected = hashlib.sha256(
            canonical_json(self._payload_for_signature()).encode()
        ).hexdigest()
        return bool(self.signature) and self.signature == expected
