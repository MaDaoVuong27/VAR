# -*- coding: utf-8 -*-
"""Synthetic v5 — sinh document bằng KHUNG CÂU trích từ test (transductive, entity-first).

Xem docs/SYNTHETIC_V5_PLAN.md IDEA 7 cho toàn bộ lý do + ranh giới. Tóm tắt:
  - Khung (`data/patterns/frames.json`) là CẤU TRÚC (bullet/nhãn/thứ tự), KHÔNG chứa nội dung
    y khoa cụ thể của test — mọi entity trong khung gốc đã bị đục lỗ thành {TYPE} bởi
    scripts/mine_frames.py trước khi lưu.
  - Chỉ dùng khung có `"safe": true` (residual ngắn, đã lọc khung mang theo nội dung cụ thể).
  - Entity điền vào slot luôn lấy từ KB (ICD-10/RxNorm) hoặc lexicon — KHÔNG bao giờ từ test.

Điểm khác biệt cốt lõi so với `generate.py` (Cấp 2) và `llm_prose.py` (Cấp 3):
  - `generate.py`: khung do NGƯỜI viết tay (đa dạng thấp, nhưng không có rủi ro leakage).
  - `llm_prose.py`: khung do LLM tự nghĩ (đa dạng cao, cần verifier vì LLM có thể sai cue).
  - `frame_generate.py` (module này): khung MINED từ chính phân phối test thật, nhưng vẫn
    KHÔNG LLM — assertion được ÉP theo cue chữ trong khung (xem `_cue_forced_assertion`), nên
    nhãn LUÔN khớp text theo thiết kế, không cần verifier hậu kiểm.

Usage:
    python -m src.synthetic.frame_generate --n 700 --out data/synthetic/frame_v5.jsonl --seed 5
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .catalog import Catalog
from . import lexicons as LEX

_ROOT = Path(__file__).resolve().parent.parent.parent
_FRAMES_PATH = _ROOT / "data" / "patterns" / "frames.json"

H = ["isHistorical"]
N = ["isNegated"]
F = ["isFamily"]

# Xác suất CÓ assertion theo type — đo trên dev gold (xem SYNTHETIC_V5_PLAN.md §2).
# CHẨN_ĐOÁN 36/44=81.8%, THUỐC 14/20=70.0%, TRIỆU_CHỨNG 20/54=37.0%.
_P_HAS_ASSERT = {"CHẨN_ĐOÁN": 0.818, "THUỐC": 0.70, "TRIỆU_CHỨNG": 0.37}
# Nếu CÓ assertion (không bị cue ép), phân bổ giữa 3 loại theo tỉ lệ dev gold tổng
# (isHistorical 51, isNegated 16, isFamily 3 -> 73%/23%/4%). KHÔNG sinh combo — dev gold đo
# được 0% concept có >1 assertion; combo trong prose cũ (7%) là artifact của roll độc lập.
_ASSERT_KIND = [(H, 0.73), (N, 0.23), (F, 0.04)]

_NEG_CUE_RE = re.compile(r"\bkhông\b|\bphủ nhận\b|\bkhông ghi nhận\b|\bkhông có\b", re.IGNORECASE)
_HIST_CUE_RE = re.compile(
    r"tiền sử|trước khi nhập viện|mãn tính|trước đây|đã hết thuốc|đã dùng", re.IGNORECASE
)


def _cue_forced_assertion(template: str) -> Optional[List[str]]:
    """Nếu khung có cue rõ ràng trong CHÍNH VĂN BẢN, ép assertion khớp cue thay vì roll ngẫu
    nhiên -> nhãn LUÔN đúng theo thiết kế (khác LLM: không cần verifier phát hiện LLM nói dối).
    Trả None nếu khung không có cue rõ -> gọi nơi khác roll theo _P_HAS_ASSERT/_ASSERT_KIND.
    """
    if _NEG_CUE_RE.search(template):
        return list(N)
    if _HIST_CUE_RE.search(template):
        return list(H)
    return None


def _roll_assertion(rng: random.Random, typ: str) -> List[str]:
    p = _P_HAS_ASSERT.get(typ, 0.0)
    if rng.random() >= p:
        return []
    r = rng.random()
    acc = 0.0
    for kind, w in _ASSERT_KIND:
        acc += w
        if r < acc:
            return list(kind)
    return list(_ASSERT_KIND[-1][0])


class FrameCatalog:
    def __init__(self, path: Path = _FRAMES_PATH):
        self.path = path
        self.frames: List[dict] = []
        self.skeleton: List[dict] = []
        self.line_kind: dict = {}

    def load(self) -> "FrameCatalog":
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.frames = [f for f in data["frames"] if f.get("safe", True)]
        self.skeleton = data.get("skeleton_headers", [])
        self.line_kind = data.get("line_kind_dist", {})
        if not self.frames:
            raise SystemExit(f"[frame_generate] Không có khung 'safe' nào trong {self.path}")
        return self

    def sample_frame(self, rng: random.Random) -> dict:
        weights = [f["freq"] for f in self.frames]
        return rng.choices(self.frames, weights=weights, k=1)[0]

    def sample_header(self, rng: random.Random) -> str:
        weights = [h["freq"] for h in self.skeleton]
        return rng.choices(self.skeleton, weights=weights, k=1)[0]["text"]


class Builder:
    """Giống Builder trong generate.py — offset = độ dài chuỗi hiện tại lúc chèn."""

    def __init__(self):
        self.parts: List[str] = []
        self.len = 0
        self.concepts: List[dict] = []

    def lit(self, s: str):
        self.parts.append(s)
        self.len += len(s)

    def ent(self, text: str, typ: str, assertions=None, candidates=None):
        start = self.len
        self.parts.append(text)
        self.len += len(text)
        self.concepts.append({
            "text": text, "type": typ, "position": [start, self.len],
            "assertions": assertions or [], "candidates": candidates or [],
        })

    def build(self):
        return "".join(self.parts), self.concepts


def _fill_slot(typ: str, cat: Catalog, rng: random.Random) -> Tuple[str, List[str]]:
    """Trả (text, candidates) cho 1 slot theo type. Không xử lý assertion ở đây."""
    if typ == "CHẨN_ĐOÁN":
        d = cat.natural_disease()
        return d.text, list(d.candidates)
    if typ == "THUỐC":
        dr = cat.drug()
        text = dr.text
        if rng.random() < 0.5:
            text += " " + rng.choice(LEX.DRUG_DOSES)
        if rng.random() < 0.35:
            text += " " + rng.choice(LEX.DRUG_ROUTES)
        return text, list(dr.candidates)
    if typ == "TRIỆU_CHỨNG":
        return cat.symptom(), []
    if typ == "TÊN_XÉT_NGHIỆM":
        return cat.test(), []
    if typ == "KẾT_QUẢ_XÉT_NGHIỆM":
        if rng.random() < 0.8:
            val = str(rng.randint(1, 400))
            if rng.random() < 0.5:
                val += "." + str(rng.randint(0, 9))
            unit = rng.choice(LEX.UNITS)
            return (val + (" " + unit if unit else "")).strip(), []
        return rng.choice(LEX.RESULT_PHRASES), []
    raise ValueError(f"Unknown slot type: {typ}")


def _emit_frame(b: Builder, frame: dict, cat: Catalog, rng: random.Random):
    """Điền 1 khung vào builder. Slot cùng loại trong 1 khung lab (TÊN_XN + KẾT_QUẢ_XN) được
    gán CHUNG 1 assertion roll (vì cùng 1 mệnh đề), các type khác roll độc lập theo slot.
    """
    template = frame["template"]
    types = frame["types"]
    forced = _cue_forced_assertion(template)

    parts = re.split(r"(\{[^}]+\})", template)
    ti = 0
    for part in parts:
        m = re.fullmatch(r"\{([^}]+)\}", part)
        if not m:
            b.lit(part)
            continue
        typ = types[ti]
        ti += 1
        text, cands = _fill_slot(typ, cat, rng)
        if typ in ("CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"):
            asserts = forced if forced is not None else _roll_assertion(rng, typ)
        else:
            asserts = []
        b.ent(text, typ, asserts, cands)


# Filler O (không entity) — dùng skeleton mined + vài câu tường thuật trung tính TỰ VIẾT
# (không lấy nguyên câu tường thuật từ test, chỉ dùng header layout đã đục lỗ sẵn).
_NEUTRAL_FILLER = [
    "Bệnh nhân tỉnh, tiếp xúc tốt.", "Diễn biến trong viện ổn định.",
    "Được theo dõi định kỳ tại chuyên khoa.", "Đã hội chẩn chuyên khoa.",
    "Bệnh nhân được chuyển khoa điều trị.", "Lên lịch tái khám.",
    "Bệnh nhân ổn định khi ra viện.", "Được chỉ định điều trị tiếp tục.",
    "Bệnh nhân được thăm khám bởi bác sĩ phụ trách chính trong ca trực.",
    "Các chỉ số sinh tồn trong giới hạn bình thường, chưa ghi nhận bất thường mới.",
    "Kế hoạch điều trị tiếp theo sẽ được hội chẩn lại vào buổi sáng hôm sau.",
    "Gia đình bệnh nhân đã được giải thích về tình trạng hiện tại và đồng thuận điều trị.",
    "Hồ sơ bệnh án được cập nhật đầy đủ sau mỗi lần thăm khám.",
]


def gen_document(cat: Catalog, fc: FrameCatalog, rng: random.Random, target_len: int):
    """Mật độ entity: đo được bản đầu 49/doc (~1 entity mỗi 25 ký tự) — DÀY HƠN cả ví dụ đậm đặc
    nhất của đề (1/28, danh sách xét nghiệm liên tiếp). Nguyên nhân: khung 1-slot ngắn
    ("- {CHẨN_ĐOÁN}") tốn rất ít target_len/iteration nhưng vẫn cộng 1 entity -> nhiều vòng lặp
    lọt qua trước khi đạt target_len. Tăng tỉ lệ non-entity (header+filler) 20%->45% để giảm mật
    độ, giữ đúng phân bố kiểu dòng đo được ở tầng 2 (bullet 58% không đồng nghĩa 58% có entity —
    nhiều dòng bullet trong note thật là filler/mô tả, không phải khái niệm)."""
    b = Builder()
    guard = 0
    while b.len < target_len and guard < 120:
        guard += 1
        r = rng.random()
        if r < 0.15 and fc.skeleton:
            b.lit(fc.sample_header(rng) + "\n")
        elif r < 0.45:
            b.lit(rng.choice(_NEUTRAL_FILLER) + "\n")
        else:
            frame = fc.sample_frame(rng)
            _emit_frame(b, frame, cat, rng)
            b.lit("\n")
    return b.build()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=700)
    ap.add_argument("--out", default="data/synthetic/frame_v5.jsonl")
    ap.add_argument("--frames", default=str(_FRAMES_PATH))
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args()

    cat = Catalog(seed=args.seed).load()
    fc = FrameCatalog(Path(args.frames)).load()
    rng = random.Random(args.seed)

    out = _ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    bad = 0
    lens = []
    with open(out, "w", encoding="utf-8") as f:
        for _ in range(args.n):
            target = min(4428, max(136, int(rng.lognormvariate(7.11, 0.62))))
            text, concepts = gen_document(cat, fc, rng, target)
            for c in concepts:
                if text[c["position"][0]:c["position"][1]] != c["text"]:
                    bad += 1
            lens.append(len(text))
            f.write(json.dumps({"text": text, "concepts": concepts}, ensure_ascii=False) + "\n")
    lens.sort()
    print(f"Wrote {args.n} docs -> {out} | offset errors: {bad}")
    print(f"Độ dài: min={lens[0]} median={lens[len(lens)//2]} max={lens[-1]}")
    print(f"Khung dùng: {len(fc.frames)} (safe) | header: {len(fc.skeleton)}")


if __name__ == "__main__":
    main()
