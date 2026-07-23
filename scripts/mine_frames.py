# -*- coding: utf-8 -*-
"""Trích pattern từ 100 file test (transductive, xem docs/SYNTHETIC_V5_PLAN.md IDEA 7).

CHỈ lấy KHUNG (cách viết), KHÔNG lấy NỘI DUNG (viết về cái gì) — nguyên tắc bắt buộc:
  - Entity trong predictions bị ĐỤC LỖ thành {TYPE} trước khi lưu -> khung không chứa
    tên bệnh/thuốc/triệu chứng cụ thể nào của test.
  - Header/skeleton là layout thuần (không phải tri thức y khoa).
  - Không lưu câu nguyên văn còn entity thật.

4 tầng trích (khớp §IDEA 7 SYNTHETIC_V5_PLAN.md):
  1. skeleton   : header xuất hiện >=N file -> khung tài liệu
  2. line_kind  : phân bố bullet/nhãn:giá trị/đánh số/văn xuôi -> canh tỉ lệ generator
  3. frames     : dòng đã đục lỗ entity -> khung câu tái dùng (phần giá trị nhất)
  4. noise_stats: thống kê nhiễu bề mặt (glue, độ dài) -> tham số hoá, không lấy chuỗi

Lọc bắt buộc trước khi dùng (khung đến từ chính predictions -> mang theo lỗi NER):
  - bỏ khung tần suất 1 (không đủ tin cậy là pattern thật)
  - bỏ khung có >=2 slot CÙNG TYPE liền nhau (nghi artifact tách/gộp span sai)

Usage:
    python scripts/mine_frames.py --pred experiments/exp_0024_boundary_fix/predictions_test \
        --input data/raw_new/input --out data/patterns/frames.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_HDR_NUM = re.compile(r"^\d+\.\s")
_TYPES = ["TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "THUỐC", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"]


def _load_predictions(pred_dir: Path):
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in pred_dir.glob("*.json")}


def _blank_entities(raw: str, concepts: list) -> str:
    """Thay mỗi span bằng {TYPE}, xử lý từ cuối văn bản lên đầu để offset không lệch."""
    out = raw
    for c in sorted(concepts, key=lambda x: -x["position"][0]):
        s, e = c["position"]
        out = out[:s] + "{" + c["type"] + "}" + out[e:]
    return out


def mine_skeleton(docs: list, min_freq: int = 5):
    hdr = Counter()
    for d in docs:
        for line in d.split("\n"):
            t = line.strip()
            if not t or len(t) > 60:
                continue
            is_numbered = bool(_HDR_NUM.match(t))
            is_short_colon = t.endswith(":") and len(t.split()) <= 7
            is_titlecase_short = t[:1].isupper() and len(t.split()) <= 6 and not t.endswith(".")
            if is_numbered or is_short_colon or is_titlecase_short:
                hdr[t.rstrip(":")] += 1
    return [{"text": h, "freq": n} for h, n in hdr.most_common() if n >= min_freq]


def mine_line_kind(docs: list):
    kinds = Counter()
    for d in docs:
        for line in d.split("\n"):
            t = line.strip()
            if not t:
                continue
            if re.match(r"^[-*+•]\s", t):
                kinds["bullet"] += 1
            elif re.match(r"^\d+[.)]\s", t):
                kinds["numbered"] += 1
            elif re.match(r"^[^:]{2,40}:\s*\S", t):
                kinds["label_value"] += 1
            elif re.match(r"^[^:]{2,40}:\s*$", t):
                kinds["label_empty"] += 1
            elif len(t.split()) > 18:
                kinds["prose_long"] += 1
            else:
                kinds["short_other"] += 1
    tot = sum(kinds.values()) or 1
    return {k: round(v / tot, 4) for k, v in kinds.most_common()}


_SLOT = re.compile(r"\{[^}]+\}")
# residual quá dài -> nghi NER bỏ sót 1 phần câu, để lại nội dung Y KHOA CỤ THỂ của test lẫn vào
# khung (khác lỗi "gộp sai type" — đây là lỗi "thiếu tag"). Không xoá, chỉ gắn cờ để generator
# mặc định bỏ qua, giữ minh bạch cho người review (xem SYNTHETIC_V5_PLAN.md IDEA 7 "ranh giới").
_MAX_RESIDUAL_WORDS = 5


def _residual_word_count(template: str) -> int:
    return len(_SLOT.sub(" ", template).split())


def mine_frames(preds: dict, inputs: dict, min_freq: int = 2):
    frames = Counter()
    frame_types: dict = {}
    for stem, concepts in preds.items():
        raw = inputs.get(stem)
        if raw is None:
            continue
        blanked = _blank_entities(raw, concepts)
        for line in blanked.split("\n"):
            t = re.sub(r"\s+", " ", line).strip()
            if "{" not in t or not (3 <= len(t) <= 95):
                continue
            frames[t] += 1
            if t not in frame_types:
                frame_types[t] = re.findall(r"\{([^}]+)\}", t)

    kept, dropped_freq, dropped_adjacent = [], 0, 0
    n_unsafe = 0
    for t, n in frames.items():
        if n < min_freq:
            dropped_freq += 1
            continue
        types = frame_types[t]
        if any(types[i] == types[i + 1] for i in range(len(types) - 1)):
            dropped_adjacent += 1
            continue
        safe = _residual_word_count(t) <= _MAX_RESIDUAL_WORDS
        n_unsafe += not safe
        kept.append({"template": t, "types": types, "freq": n, "safe": safe})
    kept.sort(key=lambda x: -x["freq"])
    return kept, {"total_raw": len(frames), "dropped_freq1": dropped_freq,
                  "dropped_adjacent_same_type": dropped_adjacent, "kept": len(kept),
                  "flagged_unsafe_residual": n_unsafe}


def mine_noise_stats(docs: list):
    lens = sorted(len(d) for d in docs)
    glue = re.compile(r"[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợ"
                       r"ùúủũụưứừửữựỳýỷỹỵđ][A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]")
    n_glue = sum(1 for d in docs if glue.search(d))
    return {
        "n_docs": len(docs),
        "len_min": lens[0], "len_median": lens[len(lens) // 2], "len_max": lens[-1],
        "pct_doc_has_glue": round(n_glue / max(len(docs), 1), 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="experiments/exp_0024_boundary_fix/predictions_test")
    ap.add_argument("--input", default="data/raw_new/input")
    ap.add_argument("--out", default="data/patterns/frames.json")
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--min-header-freq", type=int, default=5)
    args = ap.parse_args()

    pred_dir = ROOT / args.pred
    input_dir = ROOT / args.input
    if not input_dir.exists():
        input_dir = ROOT / "data" / "raw" / "input"

    preds = _load_predictions(pred_dir)
    inputs = {p.stem: p.read_text(encoding="utf-8") for p in input_dir.glob("*.txt")}
    docs = list(inputs.values())

    skeleton = mine_skeleton(docs, min_freq=args.min_header_freq)
    line_kind = mine_line_kind(docs)
    frames, frame_stats = mine_frames(preds, inputs, min_freq=args.min_freq)
    noise = mine_noise_stats(docs)

    out = {
        "source": {"pred_dir": args.pred, "input_dir": str(input_dir.relative_to(ROOT))},
        "skeleton_headers": skeleton,
        "line_kind_dist": line_kind,
        "frame_stats": frame_stats,
        "frames": frames,
        "noise_stats": noise,
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"skeleton headers (freq>={args.min_header_freq}): {len(skeleton)}")
    print(f"line_kind_dist: {line_kind}")
    print(f"frames: {frame_stats}")
    print(f"noise_stats: {noise}")
    print(f"\nTop 15 frames giữ lại:")
    for f in frames[:15]:
        flag = "" if f["safe"] else "  ⚠️ UNSAFE (residual dài, xem lại tay)"
        print(f"  {f['freq']:4d}x  {f['template']}{flag}")
    unsafe = [f for f in frames if not f["safe"]]
    if unsafe:
        print(f"\n{len(unsafe)} khung bị gắn cờ UNSAFE (residual > {_MAX_RESIDUAL_WORDS} từ) — "
              f"generator MẶC ĐỊNH bỏ qua, cần review tay trước khi whitelist:")
        for f in unsafe:
            print(f"  {f['freq']:4d}x  {f['template']}")
    print(f"\nWrote -> {out_path}")


if __name__ == "__main__":
    main()
