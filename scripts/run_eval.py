"""Chấm điểm predictions so với ground_truth đã xác minh.

Chỉ chấm trên các file có trong --gold (nhãn đã xác minh). Nếu ground_truth/ rỗng thì
báo và thoát (chưa có gì để chấm — xem data/labeled/ground_truth/README.md).

Usage:
    python scripts/run_eval.py \
        --pred experiments/exp_0001_baseline/predictions \
        --gold data/labeled/ground_truth
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.io_utils import load_gold_dir, read_gold  # noqa: E402
from src.eval.metric import score_dataset, score_sample  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gold", default="data/labeled/ground_truth")
    ap.add_argument("--per-file", action="store_true", help="in điểm từng file")
    args = ap.parse_args()

    golds = load_gold_dir(args.gold)
    golds = {k: v for k, v in golds.items()}  # bỏ README (không phải .json)
    if not golds:
        print(f"[run_eval] Chưa có nhãn đã xác minh trong {args.gold} — chưa chấm được.")
        print("  Xem data/labeled/ground_truth/README.md để biết cách tạo nhãn.")
        return

    pred_dir = Path(args.pred)
    preds = {}
    for stem in golds:
        p = pred_dir / f"{stem}.json"
        preds[stem] = read_gold(p) if p.exists() else []

    if args.per_file:
        print(f"{'file':8s} {'text':>7s} {'assert':>7s} {'cand':>7s}")
        for stem in sorted(golds, key=lambda s: (len(s), s)):
            ts, ja, cn, cd = score_sample(preds[stem], golds[stem])
            cs = cn / cd if cd else 1.0
            print(f"{stem:8s} {ts:7.3f} {ja:7.3f} {cs:7.3f}")

    s = score_dataset(preds, golds)
    print(f"\n=== Scores trên {len(golds)} file đã xác minh ===")
    print(json.dumps(s.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
