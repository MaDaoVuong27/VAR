# -*- coding: utf-8 -*-
"""Chẩn đoán lỗi biên/type/recall giữa predictions và gold — tách theo type.

Phân loại mỗi gold concept (trên type có candidate: CHẨN_ĐOÁN/THUỐC, hoặc toàn bộ nếu --all-types):
  exact       : pred trùng type + trùng CẢ 2 biên
  boundary    : pred trùng type, overlap, nhưng SAI biên (trái/phải/cả hai)
  wrong_type  : pred overlap nhưng SAI type
  missed      : không có pred nào overlap
  + spurious  : pred không overlap gold nào (thừa)

Dùng để dựng baseline TRƯỚC/SAU mỗi thay đổi (sửa _snap_word, sửa dev gold, đổi NER...).
Không phụ thuộc `src/eval/metric.py` (đây là chẩn đoán chi tiết hơn, không phải điểm số).

Usage:
    python scripts/diagnose_boundary.py --pred experiments/exp_0022_assert_clf/predictions \
        --gold data/labeled/ground_truth --all-types
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

CANDIDATE_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}


def _load_dir(d: Path) -> Dict[str, list]:
    out = {}
    for p in sorted(d.glob("*.json")):
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def _boundary_kind(gs: int, ge: int, ps: int, pe: int) -> str:
    left_off = ps != gs
    right_off = pe != ge
    if left_off and right_off:
        return "both"
    if left_off:
        return "left"
    return "right"


def diagnose(preds: Dict[str, list], golds: Dict[str, list], types=None):
    counts = Counter()
    by_type = defaultdict(Counter)
    boundary_kind = Counter()
    examples = defaultdict(list)

    for stem, gold in golds.items():
        pred = preds.get(stem, [])
        used_p = set()
        for g in gold:
            if types and g["type"] not in types:
                continue
            gs, ge = g["position"]
            best = None
            for i, p in enumerate(pred):
                if i in used_p:
                    continue
                ps, pe = p["position"]
                ov = max(0, min(ge, pe) - max(gs, ps))
                if ov > 0 and (best is None or ov > best[1]):
                    best = (i, ov, p)
            if best is None:
                counts["missed"] += 1
                by_type[g["type"]]["missed"] += 1
                examples["missed"].append((stem, g["text"]))
                continue
            i, ov, p = best
            used_p.add(i)
            ps, pe = p["position"]
            if p["type"] != g["type"]:
                counts["wrong_type"] += 1
                by_type[g["type"]]["wrong_type"] += 1
                examples["wrong_type"].append((stem, g["text"], p["text"], p["type"]))
            elif (ps, pe) != (gs, ge):
                counts["boundary"] += 1
                by_type[g["type"]]["boundary"] += 1
                bk = _boundary_kind(gs, ge, ps, pe)
                boundary_kind[bk] += 1
                examples["boundary"].append((stem, g["text"], p["text"]))
            else:
                counts["exact"] += 1
                by_type[g["type"]]["exact"] += 1
        spurious = [p for i, p in enumerate(pred) if i not in used_p
                    and (not types or p["type"] in types)]
        counts["spurious"] += len(spurious)

    return counts, by_type, boundary_kind, examples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gold", default="data/labeled/ground_truth")
    ap.add_argument("--all-types", action="store_true",
                    help="chẩn đoán trên cả 5 type (mặc định chỉ CHẨN_ĐOÁN/THUỐC)")
    ap.add_argument("--examples", type=int, default=8, help="số ví dụ in ra mỗi nhóm lỗi")
    args = ap.parse_args()

    preds = _load_dir(ROOT / args.pred)
    golds = _load_dir(ROOT / args.gold)
    types = None if args.all_types else CANDIDATE_TYPES

    counts, by_type, bkind, examples = diagnose(preds, golds, types)
    tot = sum(counts[k] for k in ("exact", "boundary", "wrong_type", "missed"))

    scope = "5 type" if args.all_types else "CHẨN_ĐOÁN/THUỐC"
    print(f"=== Chẩn đoán biên ({scope}) — pred={args.pred} vs gold={args.gold} ===\n")
    print(f"Tổng {tot} gold concept:")
    for k in ("exact", "boundary", "wrong_type", "missed"):
        print(f"  {k:<12s} {counts[k]:4d} ({100*counts[k]/max(tot,1):5.1f}%)")
    print(f"  {'spurious':<12s} {counts['spurious']:4d}  (pred thừa, không tính % trên gold)")

    if bkind:
        print(f"\nPhân loại lỗi biên (n={sum(bkind.values())}):")
        for k, v in bkind.most_common():
            print(f"  lệch {k:<6s} {v:3d}")

    print("\nTheo type:")
    print(f"  {'type':<20s} {'exact':>6s} {'boundary':>9s} {'wrong_type':>11s} {'missed':>7s}")
    for t, c in by_type.items():
        print(f"  {t:<20s} {c['exact']:6d} {c['boundary']:9d} {c['wrong_type']:11d} {c['missed']:7d}")

    for grp in ("boundary", "wrong_type", "missed"):
        if not examples[grp]:
            continue
        print(f"\nVí dụ '{grp}' (tối đa {args.examples}):")
        for ex in examples[grp][: args.examples]:
            print(f"  {ex}")


if __name__ == "__main__":
    main()
