"""Audit round 2 (stream ork) regression test; fails on master b3c7c90 (finding ORK2-05)."""

from __future__ import annotations

from nodestro_integrations.ocr import MAX_PAGE_PIXELS, _dpi


def test_ork2_page_pixels_stay_within_the_limit_for_huge_pages() -> None:
    # pdfinfo prints sizes up to 999999 pt without an exponent; at the old 1 dpi floor that is 193 Mpx.
    width = height = 999_999.0
    dpi = _dpi(width, height)
    if dpi is not None:  # None: the page is refused (the fix); a resolution must keep the limit.
        pixels = (width * dpi / 72) * (height * dpi / 72)
        assert pixels <= MAX_PAGE_PIXELS
    assert dpi is None
