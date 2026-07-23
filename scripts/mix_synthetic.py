# -*- coding: utf-8 -*-
"""Phối trộn frame_v5.jsonl + prose_v5.jsonl theo tỉ lệ ENTITY mong muốn (không phải tỉ lệ doc).

Vì mỗi frame-doc và mỗi prose-doc có mật độ entity khác nhau, trộn theo SỐ DOC sẽ cho tỉ lệ
entity lệch hẳn ý định. Script này đếm entity thật của từng nguồn rồi chọn số doc sao cho khớp
tỉ lệ entity mục tiêu.

Usage:
    python scripts/mix_synthetic.py --frame data/synthetic/frame_v5.jsonl \
        --prose data/synthetic/prose_v5.jsonl --prose-entity-share 0.15 \
        --out data/synthetic/train_v5a.jsonl --seed 1
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _n_entities(rows):
    return sum(len(r["concepts"]) for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True)
    ap.add_argument("--prose", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prose-entity-share", type=float, required=True,
                    help="tỉ lệ ENTITY (không phải doc) muốn đến từ prose, vd 0.15 hoặc 0.30")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    frame_rows = _load(ROOT / args.frame)
    prose_rows = _load(ROOT / args.prose)
    rng.shuffle(frame_rows)
    rng.shuffle(prose_rows)

    frame_ent_per_doc = _n_entities(frame_rows) / max(len(frame_rows), 1)
    prose_ent_per_doc = _n_entities(prose_rows) / max(len(prose_rows), 1)

    # target: prose_entities / (prose_entities + frame_entities) = share
    # dùng TOÀN BỘ prose có sẵn, tính số frame-doc cần để đạt đúng tỉ lệ.
    prose_entities = _n_entities(prose_rows)
    target_frame_entities = prose_entities * (1 - args.prose_entity_share) / args.prose_entity_share
    n_frame_needed = max(1, min(len(frame_rows), round(target_frame_entities / frame_ent_per_doc)))

    mixed = prose_rows + frame_rows[:n_frame_needed]
    rng.shuffle(mixed)

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in mixed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    final_prose_ent = prose_entities
    final_frame_ent = _n_entities(frame_rows[:n_frame_needed])
    final_share = final_prose_ent / max(final_prose_ent + final_frame_ent, 1)

    print(f"frame: {len(frame_rows)} doc có sẵn ({frame_ent_per_doc:.1f} entity/doc)")
    print(f"prose: {len(prose_rows)} doc có sẵn ({prose_ent_per_doc:.1f} entity/doc)")
    print(f"-> dùng {n_frame_needed} frame-doc + {len(prose_rows)} prose-doc"
          f" = {len(mixed)} doc tổng")
    print(f"tỉ lệ entity từ prose: mục tiêu {args.prose_entity_share:.0%}, "
          f"thực tế {final_share:.1%}")
    print(f"Wrote -> {out_path}")


if __name__ == "__main__":
    main()
