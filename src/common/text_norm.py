"""Chuẩn hoá text — CHỈ dùng cho so khớp/KB, KHÔNG đổi raw text (giữ offset gốc).

Xem docs/EDA_FINDINGS.md §2: position chấm theo offset ký tự trên raw text gốc, nên
mọi chuẩn hoá ở đây chỉ phục vụ matching, không được áp lại lên chuỗi gốc.
"""
from __future__ import annotations

import re
from typing import Tuple

from unidecode import unidecode

_WS = re.compile(r"\s+")
# ký tự rác hay bám 2 đầu span
_STRIP_CHARS = " \t\r\n.,;:*-–—•+()[]\"'"


def normalize_for_match(s: str, drop_diacritics: bool = False) -> str:
    """Lower + gộp khoảng trắng + strip. drop_diacritics=True để so khớp bỏ dấu."""
    s = _WS.sub(" ", s.strip().lower())
    if drop_diacritics:
        s = unidecode(s)
    return s


def strip_span(raw: str, start: int, end: int) -> Tuple[int, int]:
    """Co [start,end) về sát nội dung thật (bỏ khoảng trắng/ký tự rác 2 đầu).

    Trả offset mới (vẫn trên raw). Dùng khi cắt span theo dòng/bullet mà dính rác.
    """
    while start < end and raw[start] in _STRIP_CHARS:
        start += 1
    while end > start and raw[end - 1] in _STRIP_CHARS:
        end -= 1
    return start, end
