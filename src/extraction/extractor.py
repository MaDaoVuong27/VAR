"""NER heuristic (Tier 0) — bám cấu trúc mục + bullet + cue nội dung, giữ offset raw.

Chiến lược (baseline, ưu tiên precision hợp lý hơn recall tối đa):
- Chỉ trích từ dòng bullet (`- * +`) và dòng "nhãn: giá trị" (vd "Lý do nhập viện:"),
  bỏ qua đoạn văn tường thuật dài để tránh false-positive.
- Type suy ra từ: (1) section/sub-context đang đứng, (2) cue nội dung (liều thuốc, tên
  thuốc trong RxNorm vocab, từ khoá xét nghiệm + số).
- Offset (`position`) luôn tính trên raw text gốc (xem docs/EDA_FINDINGS.md §2).

Trả list (text, type, start, end, section) — assertion/candidate gắn ở bước sau.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from ..common.text_norm import normalize_for_match, strip_span
from ..schema import (
    TYPE_CHAN_DOAN,
    TYPE_KQ_XN,
    TYPE_TEN_XN,
    TYPE_THUOC,
    TYPE_TRIEU_CHUNG,
)

# ---------- regex/cue ----------
_BULLET = re.compile(r"^(\s*(?:[-*+•]|\d+[.)]|\*\s*\d+[.)])\s+)")
_DOSE = re.compile(r"\b\d+([.,]\d+)?\s?(mg|mcg|ml|g|iu|units?)\b", re.IGNORECASE)
_ROUTE = re.compile(r"\b(po|iv|im|sc|bid|tid|qid|qd|qhs|qam|q\d+h|prn|nebs?|daily)\b", re.IGNORECASE)
_NUM = re.compile(r"\d+([.,]\d+)?")
_MD = re.compile(r"\*\*|__")

# từ khoá xét nghiệm (tên xét nghiệm)
_LAB_KW = re.compile(
    r"\b(wbc|neut%?|lymp?h%?|hgb|hct|plt|rbc|troponin|creatinin[e]?|glucose|inr|"
    r"alt|ast|ure|urea|bun|spo2|natri|kali|bạch cầu|tiểu cầu|hồng cầu|men gan|"
    r"tổng phân tích|công thức máu|chức năng gan|nước tiểu|đường huyết|điện tâm đồ|"
    r"ecg|x-quang|siêu âm|ct|mri|holter)\b",
    re.IGNORECASE,
)

# header -> (top_section, sub_context)
_HEADERS = [
    (re.compile(r"tiền sử bệnh hiện tại|bệnh sử hiện tại|lịch sử bệnh hiện tại|quá trình bệnh", re.I), ("present", None)),
    (re.compile(r"tiền sử|tiền căn", re.I), ("history", None)),
    (re.compile(r"đánh giá tại bệnh viện|khám tại bệnh viện|tại bệnh viện", re.I), ("hospital", None)),
    (re.compile(r"thuốc (trước|đã điều trị|điều trị)|thuốc trước khi|danh sách thuốc", re.I), (None, "drug")),
    (re.compile(r"bệnh (lý )?(mạn|mãn) tính|bệnh mạn|bệnh kèm|chẩn đoán", re.I), (None, "diagnosis")),
    (re.compile(r"triệu chứng|lý do (nhập viện|khám)|than phiền", re.I), (None, "symptom")),
    (re.compile(r"kết quả (xét nghiệm|phòng thí nghiệm|labo)|xét nghiệm", re.I), (None, "lab")),
    (re.compile(r"chẩn đoán hình ảnh|kết quả hình ảnh", re.I), (None, "imaging")),
    (re.compile(r"thủ thuật|phẫu thuật", re.I), (None, "procedure")),
    (re.compile(r"diễn biến|sự kiện|đặc điểm|tình trạng|yếu tố nguy cơ", re.I), (None, "narrative")),
]

# label mở đầu dòng "nhãn: giá trị" -> tách để lấy value
_LABEL = re.compile(
    r"^\s*(lý do (?:nhập viện|khám)|triệu chứng(?: hiện tại| khi (?:nhập viện|vào viện))?|"
    r"bệnh (?:lý )?(?:mạn|mãn) tính|bệnh mạn tính|thuốc(?: trước khi nhập viện| đã điều trị)?|"
    r"chẩn đoán|kết quả xét nghiệm|lý do)\s*:\s*",
    re.IGNORECASE,
)

# section không trích khái niệm (tránh nhiễu)
_SKIP_SUB = {"narrative", "procedure", "imaging"}


@dataclass
class Mention:
    text: str
    type: str
    start: int
    end: int
    section_top: Optional[str]
    section_sub: Optional[str]


def _iter_lines(raw: str):
    """Yield (line_text, start_offset) giữ offset trên raw (kể cả dòng rỗng)."""
    pos = 0
    for line in raw.splitlines(keepends=True):
        stripped = line.rstrip("\n").rstrip("\r")
        yield stripped, pos
        pos += len(line)


def _match_header(norm_line: str):
    for rx, (top, sub) in _HEADERS:
        if rx.search(norm_line):
            return top, sub
    return None


def _split_items(content: str, base: int):
    """Tách content theo dấu phẩy/;/ và trả [(item, abs_start, abs_end)] (offset raw)."""
    items = []
    for m in re.finditer(r"[^,;]+", content):
        seg = m.group(0)
        s = base + m.start()
        e = base + m.end()
        # strip rác 2 đầu (dùng chính content-local rồi cộng base ở strip_span cần raw;
        # ở đây strip thủ công trên seg)
        ls = len(seg) - len(seg.lstrip(" \t.-*+•"))
        rs = len(seg) - len(seg.rstrip(" \t.-*+•"))
        seg2 = seg[ls: len(seg) - rs]
        if seg2.strip():
            items.append((seg2.strip(), s + ls, e - rs))
    return items


def _looks_drug(text: str, kb) -> bool:
    """THUỐC nếu có route (po/iv/bid...) HOẶC có tên thuốc trong vocab — nhưng KHÔNG
    tính khi có từ khoá xét nghiệm (creatinine/troponin... cũng là 'ingredient' RxNorm).
    Liều đơn thuần (mg) không đủ (xuất hiện cả ở lab/narrative)."""
    if _LAB_KW.search(text):
        return False
    if _ROUTE.search(text):
        return True
    for tok in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text):
        if kb is not None and kb.is_drug_name(tok):
            return True
    return False


_MAX_WORDS = 10  # span dài hơn -> coi là câu tường thuật, bỏ


def _too_long(text: str) -> bool:
    return len(text.split()) > _MAX_WORDS


def _trim_drug(text: str) -> str:
    """Bỏ phần chú thích trong ngoặc của span thuốc (vd 'prograf (dose decreased...' -> 'prograf')."""
    cut = text.find("(")
    if cut > 0:
        text = text[:cut]
    return text.strip()


def extract_concepts(raw: str, kb=None) -> List[Mention]:
    mentions: List[Mention] = []
    top = None
    sub = None

    for line, lstart in _iter_lines(raw):
        if not line.strip():
            continue
        norm = normalize_for_match(line)

        # cập nhật section nếu là header (dòng ngắn, ít nội dung sau nhãn)
        hdr = _match_header(norm)
        label_m = _LABEL.match(line)

        # nếu là header thuần (không có value đáng kể) -> chỉ set context
        if hdr and not label_m:
            new_top, new_sub = hdr
            if new_top:
                top = new_top
                sub = None
            if new_sub is not None:
                sub = new_sub
            # header dạng "X: value" ngắn vẫn có thể mang value; nhưng để đơn giản, bỏ qua
            continue

        # xác định phần content + offset của nó trên raw
        content = line
        cstart = lstart
        if label_m:
            # "nhãn: value" -> set context theo nhãn, lấy value
            lab_hdr = _match_header(normalize_for_match(label_m.group(1)))
            if lab_hdr:
                if lab_hdr[0]:
                    top = lab_hdr[0]
                if lab_hdr[1] is not None:
                    sub = lab_hdr[1]
            content = line[label_m.end():]
            cstart = lstart + label_m.end()
        else:
            bm = _BULLET.match(line)
            if bm:
                content = line[bm.end():]
                cstart = lstart + bm.end()
            elif len(line.split()) > 18:
                # đoạn văn tường thuật dài, không bullet/label -> bỏ (tránh nhiễu)
                continue

        content = _MD.sub("", content)
        if not content.strip():
            continue

        # bỏ hẳn section tường thuật/thủ thuật/hình ảnh (nhiễu, span dài) — baseline ưu tiên precision
        if sub in _SKIP_SUB:
            continue
        # chưa vào sub-context nào -> bỏ (tránh bắt nhầm dòng nhãn lạ)
        if sub is None:
            continue

        _emit(mentions, content, cstart, raw, top, sub, kb)

    return mentions


def _emit(mentions, content, cstart, raw, top, sub, kb):
    """Phân loại + tạo Mention cho 1 content (có thể tách nhiều item)."""
    # XÉT NGHIỆM + KẾT QUẢ (ưu tiên trước drug vì lab-word không phải thuốc)
    if sub == "lab" or (_LAB_KW.search(content) and _NUM.search(content)):
        _emit_lab(mentions, content, cstart, raw, top, sub)
        return

    # THUỐC: 1 span thuốc, bỏ chú thích ngoặc, cắt liều giữ theo ví dụ đề
    if sub == "drug" or _looks_drug(content, kb):
        trimmed = _trim_drug(content)
        if trimmed and not _too_long(trimmed):
            s, e = strip_span(raw, cstart, cstart + len(trimmed))
            if e > s:
                mentions.append(Mention(raw[s:e], TYPE_THUOC, s, e, top, sub))
        return

    # CHẨN_ĐOÁN (mục bệnh mạn tính/chẩn đoán)
    if sub == "diagnosis":
        if _too_long(content):
            return
        s, e = strip_span(raw, cstart, cstart + len(content))
        if e > s:
            mentions.append(Mention(raw[s:e], TYPE_CHAN_DOAN, s, e, top, sub))
        return

    # còn lại: triệu chứng (mục triệu chứng/lý do), tách theo dấu phẩy
    for item, s, e in _split_items(content, cstart):
        if _too_long(item) or ":" in item:
            continue
        s2, e2 = strip_span(raw, s, e)
        if e2 > s2:
            mentions.append(Mention(raw[s2:e2], TYPE_TRIEU_CHUNG, s2, e2, top, sub))


def _emit_lab(mentions, content, cstart, raw, top, sub):
    """Tách tên xét nghiệm + kết quả (giá trị số) trong 1 dòng lab."""
    name_m = _LAB_KW.search(content)
    if name_m:
        s = cstart + name_m.start()
        e = cstart + name_m.end()
        s, e = strip_span(raw, s, e)
        if e > s:
            mentions.append(Mention(raw[s:e], TYPE_TEN_XN, s, e, top, sub))
    num_m = _NUM.search(content)
    if num_m:
        s = cstart + num_m.start()
        e = cstart + num_m.end()
        mentions.append(Mention(raw[s:e], TYPE_KQ_XN, s, e, top, sub))
