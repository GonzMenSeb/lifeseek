"""Confidence intervals + discovery-time correction (Task 7.4, SPEC §8).

Discovery rates are proportions estimated from few trials, so they get Wilson score
intervals (well-behaved near 0 and 1, unlike the naive Wald interval). Because a campaign
issues many gate queries, a discovery-time multiple-comparisons correction scales the
required evidence with the number of queries (a monotone, Bonferroni/e-value-style
shrink). Range targets must sit *strictly* inside the requested band — boundary values
are not accepted.
"""

from __future__ import annotations

from math import log, sqrt

# Two-sided z for the standard 95% interval; good enough for the confidences we use.
_Z_95 = 1.959963984540054


def _z_for(confidence: float) -> float:
    """z-score for a two-sided ``confidence`` level (closed form for common cases)."""
    if abs(confidence - 0.95) < 1e-9:
        return _Z_95
    if abs(confidence - 0.99) < 1e-9:
        return 2.5758293035489004
    if abs(confidence - 0.90) < 1e-9:
        return 1.6448536269514722
    # Acklam's inverse-normal approximation for the (1+confidence)/2 quantile.
    p = (1.0 + confidence) / 2.0
    return _inv_norm_cdf(p)


def _inv_norm_cdf(p: float) -> float:
    """Approximate standard-normal quantile (Acklam), accurate to ~1e-9 in the bulk."""
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = sqrt(-2.0 * log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    q = sqrt(-2.0 * log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    )


def proportion_point_estimate(successes: int, n: int) -> float:
    """Maximum-likelihood proportion ``successes / n`` (0 for ``n == 0``)."""
    if n <= 0:
        return 0.0
    return successes / n


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Returns ``(0.0, 1.0)`` for ``n == 0`` (no information). The interval is always within
    ``[0, 1]`` and contains the point estimate.
    """
    if n <= 0:
        return (0.0, 1.0)
    z = _z_for(confidence)
    p_hat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    half = (z * sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)) / denom
    # Clamp to [0, 1] and ensure the interval always contains the point estimate
    # (the Wilson bound at p_hat in {0, 1} sits just inside the boundary).
    lo = min(p_hat, max(0.0, center - half))
    hi = max(p_hat, min(1.0, center + half))
    return (lo, hi)


def evalue_threshold(n_gate_queries: int, alpha: float = 0.05) -> float:
    """Discovery-time multiple-comparisons correction.

    A Bonferroni / e-value-style shrink: the required evidence threshold is
    ``alpha / max(1, n_gate_queries)``, monotonically decreasing in the number of gate
    queries so more attempts demand stronger per-discovery evidence.
    """
    return alpha / max(1, n_gate_queries)


def range_target_strictly_inside(value: float, lo: float, hi: float) -> bool:
    """``True`` iff ``lo < value < hi`` — STRICT: boundary values are rejected."""
    return lo < value < hi
