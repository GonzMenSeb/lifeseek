# CI: nightly bitwise reproduction (release blocker)

The acceptance pipeline must be bit-reproducible (SPEC §9, §14.6). Nightly CI replays
every accepted discovery artifact through `lifeseek reproduce`, which rebuilds the spec
and candidate from the *serialized* fields only, re-runs the independent verifier and
the fail-closed novelty oracle, and compares the fresh outputs to the stored ones
bit-for-bit (canonical-JSON equality, including the verification record's signature) plus
the recipe's reproducibility fields (reference-sim hash, canonicalizer hash, Catagolue
snapshot hash, spec id). Any drift in a trust-path code module, the census snapshot, or
the verdict flips the run red. This documents the intent only — no CI runner is wired
here.

```bash
# Run nightly, once per accepted discovery artifact under runs/*/discoveries/*.json
uv run lifeseek reproduce runs/<spec_prefix>/discoveries/<discovery_id>.json
# exit 0 = bitwise match; exit 1 = MISMATCH (release blocker)
```
