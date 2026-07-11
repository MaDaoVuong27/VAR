"""Schema khái niệm y tế + (de)serialize JSON đúng format nộp bài.

Format 1 phần tử output (xem docs/TASK_SPEC.md):
    {"text","type","position":[start,end],"assertions":[...],"candidates":[...]}
- position: offset KÝ TỰ trên input gốc, 0-indexed, [start, end] (end exclusive theo
  quy ước Python; xem io_utils khi tìm offset).
- assertions: chỉ có nghĩa cho CHẨN_ĐOÁN / THUỐC / TRIỆU_CHỨNG.
- candidates: chỉ có nghĩa cho CHẨN_ĐOÁN / THUỐC.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# 5 nhãn type hợp lệ
TYPE_TRIEU_CHUNG = "TRIỆU_CHỨNG"
TYPE_TEN_XN = "TÊN_XÉT_NGHIỆM"
TYPE_KQ_XN = "KẾT_QUẢ_XÉT_NGHIỆM"
TYPE_CHAN_DOAN = "CHẨN_ĐOÁN"
TYPE_THUOC = "THUỐC"

ALL_TYPES = frozenset({
    TYPE_TRIEU_CHUNG, TYPE_TEN_XN, TYPE_KQ_XN, TYPE_CHAN_DOAN, TYPE_THUOC,
})
# type nào mang assertions / candidates
ASSERTION_TYPES = frozenset({TYPE_TRIEU_CHUNG, TYPE_CHAN_DOAN, TYPE_THUOC})
CANDIDATE_TYPES = frozenset({TYPE_CHAN_DOAN, TYPE_THUOC})

# assertion hợp lệ
ASSERT_NEGATED = "isNegated"
ASSERT_FAMILY = "isFamily"
ASSERT_HISTORICAL = "isHistorical"
ALL_ASSERTIONS = frozenset({ASSERT_NEGATED, ASSERT_FAMILY, ASSERT_HISTORICAL})


@dataclass
class Concept:
    text: str
    type: str
    position: List[int]  # [start, end], end exclusive
    assertions: List[str] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize, chỉ chèn assertions/candidates cho type phù hợp (khớp ví dụ đề)."""
        d = {"text": self.text, "type": self.type, "position": list(self.position)}
        if self.type in ASSERTION_TYPES:
            d["assertions"] = list(self.assertions)
        if self.type in CANDIDATE_TYPES:
            d["candidates"] = list(self.candidates)
        return d

    @staticmethod
    def from_dict(d: dict) -> "Concept":
        return Concept(
            text=d["text"],
            type=d["type"],
            position=list(d.get("position", [])),
            assertions=list(d.get("assertions", []) or []),
            candidates=list(d.get("candidates", []) or []),
        )
