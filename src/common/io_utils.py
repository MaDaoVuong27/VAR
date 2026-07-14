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


def _format_concept(d: dict) -> str:
    """Format 1 concept dict giống hệt layout ví dụ đề: object thụt 4 space, mỗi
    mảng (candidates/assertions/position) gọn trên 1 dòng (json.dumps mặc định sẽ
    xuống dòng từng phần tử mảng nên không dùng được ở đây)."""
    lines = ["  {"]
    keys = list(d.keys())
    for i, k in enumerate(keys):
        comma = "," if i < len(keys) - 1 else ""
        val = json.dumps(d[k], ensure_ascii=False)
        lines.append(f'    "{k}": {val}{comma}')
    lines.append("  }")
    return "\n".join(lines)


def write_output(concepts: List[Concept], path) -> None:
    """Ghi list Concept ra .json, layout khớp CHÍNH XÁC ví dụ trong TASK/de_bai_chi_tiet.md
    (thứ tự key text->type->candidates->assertions->position, mảng gọn 1 dòng)."""
    items = [_format_concept(c.to_dict()) for c in concepts]
    text = "[\n" + ",\n".join(items) + "\n]" if items else "[]"
    Path(path).write_text(text, encoding="utf-8")


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
