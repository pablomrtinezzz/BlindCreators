"""Pure retention-curve analytics (no I/O, fully unit-testable).

A curve is a list of (elapsed_ratio, watch_ratio) pairs as returned by the YouTube Analytics
API: ~100 points, elapsed_ratio in (0, 1], watch_ratio relative to the number of starts
(it can exceed 1.0 on rewatches/loops, which is common for Shorts).

Statistical caveats surfaced to the UI:
* The API gives no per-bucket sample size: curves from few views are noisy, so every result
  carries a `reliable` flag based on the view count at fetch time.
* For a 30 s Short each bucket is 0.3 s, finer than caption timing accuracy (~0.5-1 s), so
  sentence deltas are averaged over the sentence span and should be read as diagnostics,
  not causal effects.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from statistics import median

Curve = list[tuple[float, float]]


def interpolate(curve: Curve, ratio: float) -> float | None:
    """Linear interpolation of watch_ratio at `ratio` (clamped to the curve's range)."""
    if not curve:
        return None
    xs = [p[0] for p in curve]
    if ratio <= xs[0]:
        return curve[0][1]
    if ratio >= xs[-1]:
        return curve[-1][1]
    i = bisect_left(xs, ratio)
    (x0, y0), (x1, y1) = curve[i - 1], curve[i]
    if x1 == x0:
        return y1
    return y0 + (y1 - y0) * (ratio - x0) / (x1 - x0)


def smooth(curve: Curve, window: int = 3) -> Curve:
    """Centered moving average; keeps the x positions."""
    if window <= 1 or len(curve) < window:
        return list(curve)
    half = window // 2
    out: Curve = []
    for i, (x, _) in enumerate(curve):
        lo, hi = max(0, i - half), min(len(curve), i + half + 1)
        out.append((x, sum(p[1] for p in curve[lo:hi]) / (hi - lo)))
    return out


def retention_at_seconds(curve: Curve, duration_s: float, seconds: float) -> float | None:
    if duration_s <= 0:
        return None
    return interpolate(curve, min(seconds / duration_s, 1.0))


@dataclass(frozen=True)
class DropOff:
    at_sec: float
    at_ratio: float
    drop: float  # positive number: share of the audience lost over the window
    retention_before: float
    retention_after: float


def detect_drop_offs(
    curve: Curve, duration_s: float, *, skip_start_s: float = 3.0, top: int = 3, window_s: float = 2.0
) -> list[DropOff]:
    """Steepest audience losses after the hook, ignoring the final 5% (end-screen exits).

    Windows of `window_s` seconds are compared on the smoothed curve; results do not overlap.
    """
    if duration_s <= 0 or len(curve) < 5:
        return []
    sm = smooth(curve, 3)
    step = max(window_s / duration_s, 0.01)
    start = max(skip_start_s / duration_s, sm[0][0])
    end = 0.95
    candidates: list[DropOff] = []
    r = start
    while r + step <= end:
        before, after = interpolate(sm, r), interpolate(sm, r + step)
        if before is not None and after is not None and before > after:
            candidates.append(
                DropOff(
                    at_sec=round((r + step / 2) * duration_s, 1),
                    at_ratio=round(r + step / 2, 4),
                    drop=round(before - after, 4),
                    retention_before=round(before, 4),
                    retention_after=round(after, 4),
                )
            )
        r += step / 2
    picked: list[DropOff] = []
    for c in sorted(candidates, key=lambda d: d.drop, reverse=True):
        if all(abs(c.at_sec - p.at_sec) >= window_s for p in picked):
            picked.append(c)
        if len(picked) == top:
            break
    return sorted(picked, key=lambda d: d.at_sec)


@dataclass(frozen=True)
class SegmentRetention:
    idx: int
    start_sec: float
    end_sec: float
    text: str
    retention_start: float
    retention_end: float
    delta: float  # retention_end - retention_start (negative = viewers lost)
    loss_per_sec: float  # positive = audience lost per second while this line plays
    severity: str  # "leak" | "ok" | "gain"


def segment_retention(
    curve: Curve,
    duration_s: float,
    segments: list[tuple[int, float, float, str]],
    *,
    leak_per_sec: float | None = None,
) -> list[SegmentRetention]:
    """Maps each script segment onto the curve. `leak_per_sec` defaults to 1.5x the video's
    average loss rate, so the classification adapts to each video's overall slope."""
    if duration_s <= 0 or not curve:
        return []
    sm = smooth(curve, 3)
    first, last = sm[0][1], interpolate(sm, 0.95) or sm[-1][1]
    avg_rate = max((first - last) / (0.95 * duration_s), 1e-6)
    threshold = leak_per_sec if leak_per_sec is not None else 1.5 * avg_rate

    out: list[SegmentRetention] = []
    for idx, start, end, text in segments:
        if end <= start:
            continue
        rs = interpolate(sm, min(start / duration_s, 1.0))
        re_ = interpolate(sm, min(end / duration_s, 1.0))
        if rs is None or re_ is None:
            continue
        delta = re_ - rs
        rate = -delta / (end - start)
        severity = "leak" if rate >= threshold else ("gain" if delta > 0.005 else "ok")
        out.append(
            SegmentRetention(
                idx=idx,
                start_sec=round(start, 2),
                end_sec=round(end, 2),
                text=text,
                retention_start=round(rs, 4),
                retention_end=round(re_, 4),
                delta=round(delta, 4),
                loss_per_sec=round(rate, 4),
                severity=severity,
            )
        )
    return out


def median_curve(curves: list[Curve], points: int = 100) -> Curve:
    """Point-wise median across curves resampled onto a common grid."""
    curves = [c for c in curves if c]
    if not curves:
        return []
    grid = [(i + 1) / points for i in range(points)]
    out: Curve = []
    for x in grid:
        vals = [v for c in curves if (v := interpolate(c, x)) is not None]
        out.append((x, median(vals)))
    return out


def is_looping(curve: Curve, avg_view_pct: float | None) -> bool:
    """Shorts that replay: tail of the curve above 100% or average view % above 100."""
    tail = curve[-1][1] if curve else 0.0
    return tail > 1.0 or (avg_view_pct or 0) > 100
