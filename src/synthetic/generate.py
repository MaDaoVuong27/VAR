# -*- coding: utf-8 -*-
"""Sinh synthetic data có nhãn (span+type+assertion+candidate) cho train NER.

Cách làm: dựng document bằng TextBuilder, mỗi lần chèn entity thì ghi lại offset ký tự
CHÍNH XÁC (offset = độ dài chuỗi hiện tại). Trộn cấu trúc bullet + văn xuôi xen kẽ +
assertion + code-switch để model học bắt khái niệm BẤT KỂ vị trí (giải nút thắt baseline).

Output: JSONL, mỗi dòng {"text":..., "concepts":[{text,type,position,assertions,candidates}]}.

Usage: python -m src.synthetic.generate --n 8000 --out data/synthetic/train.jsonl --seed 1
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from .catalog import Catalog
from . import lexicons as LEX

H = ["isHistorical"]
N = ["isNegated"]
F = ["isFamily"]


class Builder:
    def __init__(self):
        self.parts = []
        self.len = 0
        self.concepts = []

    def lit(self, s: str):
        self.parts.append(s)
        self.len += len(s)

    def ent(self, text, typ, assertions=None, candidates=None):
        start = self.len
        self.parts.append(text)
        self.len += len(text)
        self.concepts.append({
            "text": text, "type": typ, "position": [start, self.len],
            "assertions": assertions or [], "candidates": candidates or [],
        })

    def build(self):
        return "".join(self.parts), self.concepts


def _drug_mention(cat, rng):
    """Tạo mention thuốc TRỌN: 'tên [liều] [đường dùng]' — span khớp convention đề bài
    (vd 'amlodipine 10 mg po daily'). Trả (text, candidates)."""
    dr = cat.drug()
    parts = [dr.text]
    if rng.random() < 0.6:
        parts.append(rng.choice(LEX.DRUG_DOSES))
    if rng.random() < 0.5:
        parts.append(rng.choice(LEX.DRUG_ROUTES))
    return " ".join(parts), dr.candidates


def _maybe_glue(rng) -> str:
    """Trả ' ' hoặc '' (glue) để mô phỏng nhiễu dính chữ, hoặc '\\n'."""
    r = rng.random()
    if r < 0.08:
        return ""       # dính liền
    return " "


# ---------- templates (mỗi cái append vào builder) ----------

def t_history_diseases(b, cat, rng):
    b.lit(rng.choice(["1. Tiền sử bệnh\n", "Tiền sử bệnh nội khoa\n", "Bệnh mạn tính:\n"]))
    for _ in range(rng.randint(1, 4)):
        b.lit(rng.choice(["- ", "    - ", ""]))
        d = cat.disease()
        b.ent(d.text, "CHẨN_ĐOÁN", H, d.candidates)
        b.lit("\n")


def t_medications(b, cat, rng):
    b.lit(rng.choice(["Thuốc trước khi nhập viện\n", "Thuốc đã điều trị\n", "Danh sách thuốc:\n"]))
    for _ in range(rng.randint(1, 4)):
        b.lit(rng.choice(["- ", "    - "]))
        text, cands = _drug_mention(cat, rng)  # span trọn tên+liều+route
        b.ent(text, "THUỐC", H, cands)
        b.lit("\n")


def t_symptoms(b, cat, rng):
    b.lit(rng.choice(["Triệu chứng hiện tại\n", "Lý do nhập viện: ", "Các triệu chứng:\n"]))
    n = rng.randint(2, 5)
    for i in range(n):
        b.lit(rng.choice(["- ", "    - ", ""]))
        neg = rng.random() < 0.25
        if neg:
            b.lit(rng.choice(LEX.NEG_CUES) + " ")
        b.ent(cat.symptom(), "TRIỆU_CHỨNG", N if neg else [])
        b.lit(rng.choice([",\n", "\n", ", "]))


def t_labs(b, cat, rng):
    b.lit(rng.choice(["Kết quả xét nghiệm\n", "Cận lâm sàng:\n", "Kết quả xét nghiệm: "]))
    for _ in range(rng.randint(1, 4)):
        b.lit(rng.choice(["- ", "    - ", ""]))
        b.ent(cat.test(), "TÊN_XÉT_NGHIỆM")
        b.lit(rng.choice([" là ", " ", ": "]))
        if rng.random() < 0.8:
            val = str(rng.randint(1, 400))
            if rng.random() < 0.5:
                val += "." + str(rng.randint(0, 9))
            unit = rng.choice(LEX.UNITS)
            b.ent((val + (" " + unit if unit else "")).strip(), "KẾT_QUẢ_XÉT_NGHIỆM")
        else:
            b.ent(rng.choice(LEX.RESULT_PHRASES), "KẾT_QUẢ_XÉT_NGHIỆM")
        b.lit("\n")


def t_prose_interleaved(b, cat, rng):
    """Câu văn xuôi trộn nhiều type + assertion — mô phỏng sample 6/8 (baseline chết)."""
    b.lit("Bệnh nhân ")
    if rng.random() < 0.7:
        b.lit(rng.choice(LEX.HIST_CUES) + " ")
        d = cat.disease()
        b.ent(d.text, "CHẨN_ĐOÁN", H, d.candidates)
        b.lit(", ")
    b.lit(rng.choice(["hiện ", "hiện tại ", "nhập viện vì "]))
    neg = rng.random() < 0.4
    if neg:
        b.lit(rng.choice(LEX.NEG_CUES) + " ")
    b.ent(cat.symptom(), "TRIỆU_CHỨNG", N if neg else [])
    b.lit(rng.choice([" nhưng ", " và ", ", kèm "]))
    b.ent(cat.symptom(), "TRIỆU_CHỨNG")
    if rng.random() < 0.6:
        b.lit(", được kê ")
        text, cands = _drug_mention(cat, rng)
        b.ent(text, "THUỐC", [], cands)
    b.lit(".\n")


def t_family(b, cat, rng):
    b.lit(rng.choice(LEX.FAMILY_CUES) + " ")
    if rng.random() < 0.5:
        d = cat.disease()
        b.ent(d.text, "CHẨN_ĐOÁN", F, d.candidates)
    else:
        b.ent(cat.symptom(), "TRIỆU_CHỨNG", F)
    b.lit(".\n")


# nội dung O (KHÔNG chứa khái niệm mục tiêu) — dạy model phần lớn text là O,
# chống over-predict. Gồm header đa dạng, câu tường thuật/hành chính, vital, filler.
FILLER_LINES = [
    "1. Tiền sử bệnh", "2. Bệnh sử hiện tại", "3. Đánh giá tại bệnh viện",
    "Thời điểm khởi phát triệu chứng:", "Các sự kiện trước khi nhập viện",
    "Tình trạng ngay trước khi nhập viện:", "Diễn biến bệnh", "Đặc điểm triệu chứng",
    "Các yếu tố nguy cơ liên quan", "Tiền sử phẫu thuật / thủ thuật",
    "Kết quả khám thực thể", "Các phát hiện chẩn đoán khác:", "Điều trị:",
    "Bệnh nhân tỉnh, tiếp xúc tốt.", "Bệnh nhân được chỉ định nhập viện để theo dõi.",
    "Diễn biến trong viện ổn định.", "Được theo dõi định kỳ tại chuyên khoa.",
    "Đã hội chẩn chuyên khoa.", "Bệnh nhân được chuyển khoa điều trị.",
    "Theo lời bệnh nhân kể lại.", "Vị trí: N/A", "Mức độ: N/A", "Tần suất: N/A",
    "Được thăm khám bởi bác sĩ phụ trách chính.", "Lên lịch tái khám.",
    "Sau đó đến khoa Cấp cứu.", "Được chỉ định điều trị tiếp tục.",
    "Khám các cơ quan chưa phát hiện bất thường.", "Bệnh nhân ổn định khi ra viện.",
    "Chỉ định can thiệp sau khi đánh giá đầy đủ nguy cơ và lợi ích.",
    "Quyết định chuyển viện để tiếp cận chẩn đoán chuyên sâu.",
]


def t_filler(b, cat, rng):
    for _ in range(rng.randint(1, 3)):
        b.lit(rng.choice(["", "- ", "    "]) + rng.choice(FILLER_LINES) + "\n")


TEMPLATES = [t_history_diseases, t_medications, t_symptoms, t_labs, t_prose_interleaved]


def gen_document(cat, rng):
    b = Builder()
    # trộn khối entity + NHIỀU khối filler (O) để cân bằng O:entity như text thật
    k = rng.randint(2, 4)
    blocks = [t_prose_interleaved] if rng.random() < 0.5 else []
    blocks += rng.choices(TEMPLATES, k=k)
    if rng.random() < 0.08:
        blocks.append(t_family)
    # chèn filler xen kẽ: mỗi khối entity kèm ~1 khối filler; thêm vài filler rải
    seq = []
    for blk in blocks:
        if rng.random() < 0.7:
            seq.append(t_filler)
        seq.append(blk)
        if rng.random() < 0.5:
            seq.append(t_filler)
    # ~10% doc gần như toàn filler (dạy: nhiều đoạn không có khái niệm)
    if rng.random() < 0.1:
        seq = [t_filler, t_filler, rng.choice(blocks), t_filler]
    for t in seq:
        t(b, cat, rng)
    return b.build()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--out", default="data/synthetic/train.jsonl")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent.parent
    cat = Catalog(seed=args.seed).load()
    rng = random.Random(args.seed)

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    bad = 0
    with open(out, "w", encoding="utf-8") as f:
        for _ in range(args.n):
            text, concepts = gen_document(cat, rng)
            # validate offset
            for c in concepts:
                if text[c["position"][0]:c["position"][1]] != c["text"]:
                    bad += 1
            f.write(json.dumps({"text": text, "concepts": concepts}, ensure_ascii=False) + "\n")
    print(f"Wrote {args.n} docs -> {out} | offset errors: {bad}")
    print(f"Catalog: {len(cat.diseases)} disease names, {len(cat.drugs)} drug names, "
          f"{len(cat.symptoms)} symptoms, {len(cat.tests)} tests")


if __name__ == "__main__":
    main()
