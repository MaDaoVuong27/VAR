# -*- coding: utf-8 -*-
"""Chấm lại TOÀN BỘ experiment từ predictions đã lưu (không cần model weights).

Dùng khi metric hoặc dev gold thay đổi: mọi exp trong experiments/*/predictions/ được
chấm lại bằng src/eval/metric.py hiện tại, in bảng so sánh. Không ghi đè metrics.json
trừ khi --write.

Usage:
    python scripts/rescore_all.py
    python scripts/rescore_all.py --write     # cập nhật dev_scores trong metrics.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.common.io_utils import load_gold_dir, read_gold  # noqa: E402
from src.eval.metric import score_dataset  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/labeled/ground_truth")
    ap.add_argument("--write", action="store_true",
                    help="ghi dev_scores mới vào metrics.json của từng exp")
    args = ap.parse_args()

    golds = load_gold_dir(ROOT / args.gold)
    if not golds:
        print(f"[rescore] Không có gold trong {args.gold}.")
        return

    exps = sorted(p for p in (ROOT / "experiments").glob("exp_*") if p.is_dir())
    print(f"Chấm lại trên {len(golds)} file gold\n")
    print(f"{'experiment':26s} {'text':>7s} {'assert':>7s} {'cand':>7s} {'final':>7s}")
    print("-" * 58)
    for e in exps:
        pred_dir = e / "predictions"
        if not pred_dir.exists():
            print(f"{e.name:26s} {'(không có predictions)':>31s}")
            continue
        preds = {k: (read_gold(pred_dir / f"{k}.json") if (pred_dir / f"{k}.json").exists() else [])
                 for k in golds}
        s = score_dataset(preds, golds)
        print(f"{e.name:26s} {s.text_score:7.3f} {s.assertions_score:7.3f} "
              f"{s.candidates_score:7.3f} {s.final_score:7.3f}")
        if args.write:
            mp = e / "metrics.json"
            m = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {"exp": e.name}
            m["dev_scores"] = s.as_dict()
            m["n_dev"] = len(golds)
            mp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write:
        print("\nĐã cập nhật dev_scores trong metrics.json của từng exp.")


if __name__ == "__main__":
    main()
