import pytest

from app.services import retention as rt


def linear(start=1.0, end=0.5, n=100):
    return [((i + 1) / n, start + (end - start) * (i + 1) / n) for i in range(n)]


def test_interpolate_and_clamp():
    curve = [(0.1, 1.0), (0.2, 0.8)]
    assert rt.interpolate(curve, 0.15) == pytest.approx(0.9)
    assert rt.interpolate(curve, 0.0) == 1.0
    assert rt.interpolate(curve, 1.0) == 0.8
    assert rt.interpolate([], 0.5) is None


def test_hook_at_three_seconds():
    curve = linear()
    # 3 s of a 30 s video = ratio 0.1 -> 1 - 0.5 * 0.1
    assert rt.retention_at_seconds(curve, 30, 3) == pytest.approx(0.95)
    assert rt.retention_at_seconds(curve, 0, 3) is None


def test_drop_off_detects_cliff():
    curve = [(x, 0.9 if x < 0.5 else 0.4) for x in [(i + 1) / 100 for i in range(100)]]
    drops = rt.detect_drop_offs(curve, 60, top=1)
    assert len(drops) == 1
    assert 28 <= drops[0].at_sec <= 32
    assert drops[0].drop > 0.3


def test_drop_off_ignores_end_screen():
    curve = [(x, 0.9 if x < 0.97 else 0.1) for x in [(i + 1) / 100 for i in range(100)]]
    assert rt.detect_drop_offs(curve, 60) == []


def test_segment_retention_flags_leaks():
    curve = [(x, 1.0 if x < 0.5 else (1.0 - (x - 0.5) * 1.6)) for x in [(i + 1) / 100 for i in range(100)]]
    segs = rt.segment_retention(curve, 20, [(0, 0, 9, "flat"), (1, 11, 19, "falling")])
    assert segs[0].severity in ("ok", "gain")
    assert segs[1].severity == "leak"
    assert segs[1].delta < 0


def test_median_curve_and_looping():
    a, b, c = linear(1, 0.4), linear(1, 0.6), linear(1, 0.8)
    med = rt.median_curve([a, b, c])
    assert med[-1][1] == pytest.approx(0.6)
    assert rt.is_looping(linear(1.0, 1.1), None)
    assert rt.is_looping([], 120)
    assert not rt.is_looping(linear(), 70)
