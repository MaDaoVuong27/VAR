"""Đọc input .txt / ghi output .json đúng format nộp bài + tìm offset span trên raw."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..schema import Concept


def read_input(path) -> str:
    """Đọc 1 file .txt input (raw, UTF-8, giữ nguyên mọi ký tự để tính offset)."""
    return Path(path).read_text(encoding="utf-8")


def write_output(concepts: List[Concept], path) -> None:
    """Ghi list Concept ra .json (list các dict theo format đề)."""
    data = [c.to_dict() for c in concepts]
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def read_gold(path) -> List[Concept]:
    """Đọc 1 file .json ground-truth -> list Concept."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Concept.from_dict(d) for d in data]


def load_gold_dir(gold_dir) -> Dict[str, List[Concept]]:
    """Nạp toàn bộ ground_truth/*.json -> {stem: [Concept]} (stem = '1','2',...)."""
    out: Dict[str, List[Concept]] = {}
    for p in sorted(Path(gold_dir).glob("*.json")):
        out[p.stem] = read_gold(p)
    return out


def find_span_offset(raw: str, span_text: str, start_hint: int = 0) -> Optional[List[int]]:
    """Tìm [start,end) của span_text trong raw, ưu tiên từ start_hint.

    Fallback khi extractor không tự giữ offset. Thử: exact từ hint -> exact toàn cục
    -> khớp linh hoạt khoảng trắng (raw có thể có nhiều space/xuống dòng giữa cụm).
    Trả None nếu không tìm được.
    """
    if not span_text:
        return None
    idx = raw.find(span_text, start_hint)
    if idx == -1:
        idx = raw.find(span_text)
    if idx != -1:
        return [idx, idx + len(span_text)]
    # khớp linh hoạt: mỗi khoảng trắng trong span match \s+ trong raw
    pattern = re.sub(r"\s+", r"\\s+", re.escape(span_text.strip()).replace("\\ ", " "))
    pattern = re.sub(r"\s+", r"\\s+", pattern)
    for base in (start_hint, 0):
        m = re.search(pattern, raw[base:])
        if m:
            return [m.start() + base, m.end() + base]
    return None
