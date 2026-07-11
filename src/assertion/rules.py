"""Gán assertion (isHistorical / isNegated / isFamily) bằng rule (Tier 0).

Chỉ áp cho CHẨN_ĐOÁN / THUỐC / TRIỆU_CHỨNG. Nguyên tắc conservative (thà bỏ sót hơn
gán bừa — xem docs/EDA_FINDINGS.md §4): chỉ gán khi cue rõ ràng.
"""
from __future__ import annotations

import re
from typing import List

from ..schema import (
    ASSERT_FAMILY,
    ASSERT_HISTORICAL,
    ASSERT_NEGATED,
    ASSERTION_TYPES,
)

# cue tiền sử (mạnh) — dùng khi không ở section history
_HIST_CUE = re.compile(
    r"tiền sử|trước khi nhập viện|trước nhập viện|trong quá khứ|tiền căn|"
    r"đã từng|bệnh (mạn|mãn) tính|trước đây|cách đây",
    re.IGNORECASE,
)

# phủ định
_NEG_CUE = re.compile(r"\bkhông\b|\bchưa\b|\bâm tính\b|\(-\)|\bloại trừ\b|\bkhông có\b|\bkhông ghi nhận\b", re.IGNORECASE)
_NEG_FALSE = re.compile(r"không xác định|không đặc hiệu|không rõ|không điển hình|không phụ thuộc", re.IGNORECASE)

# người nhà là chủ thể (không phải người kể)
_FAMILY_SUBJ = re.compile(
    r"\bbố\b|\bmẹ\b|cha mẹ|anh trai|chị gái|em trai|em gái|người thân|"
    r"thành viên (trong )?gia đình|trong gia đình (có|bị)|tiền sử gia đình|di truyền",
    re.IGNORECASE,
)
_FAMILY_NARRATOR = re.compile(r"người nhà (kể|cho biết|nhận thấy|báo)|theo lời (kể của )?người nhà", re.IGNORECASE)


def _line_around(raw: str, start: int, end: int):
    ls = raw.rfind("\n", 0, start) + 1
    le = raw.find("\n", end)
    if le == -1:
        le = len(raw)
    return raw[ls:le], ls


def _has_negation(raw: str, m) -> bool:
    line, ls = _line_around(raw, m.start, m.end)
    # xét từ đầu dòng tới hết span (cue phủ định thường đứng trước khái niệm)
    window = raw[ls:m.end]
    # bỏ các đoạn false-friend rồi mới soi cue
    cleaned = _NEG_FALSE.sub(" ", window)
    return bool(_NEG_CUE.search(cleaned))


def assign_assertions(raw: str, mentions: List) -> None:
    """Gán m.assertions tại chỗ cho các mention type có assertion."""
    for m in mentions:
        if m.type not in ASSERTION_TYPES:
            m.assertions = []
            continue
        asserts = []
        line, _ = _line_around(raw, m.start, m.end)

        # isHistorical: theo section history hoặc cue tiền sử trong dòng
        if getattr(m, "section_top", None) == "history" or _HIST_CUE.search(line):
            asserts.append(ASSERT_HISTORICAL)

        # isNegated
        if _has_negation(raw, m):
            asserts.append(ASSERT_NEGATED)

        # isFamily: có cue chủ thể người nhà và KHÔNG chỉ là người kể
        if _FAMILY_SUBJ.search(line) and not _FAMILY_NARRATOR.search(line):
            asserts.append(ASSERT_FAMILY)

        m.assertions = asserts
