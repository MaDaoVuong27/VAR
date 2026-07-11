"""Đóng gói predictions thành output.zip đúng cấu trúc nộp bài (output/{i}.json).

Usage:
    python scripts/make_submission.py \
        --pred experiments/exp_0001_baseline/predictions_test \
        --out experiments/exp_0001_baseline/output.zip
"""
import argparse
import zipfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="thư mục chứa {i}.json")
    ap.add_argument("--out", required=True, help="đường dẫn output.zip")
    args = ap.parse_args()

    pred_dir = Path(args.pred)
    files = sorted(pred_dir.glob("*.json"), key=lambda p: (len(p.stem), p.stem))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, arcname=f"output/{p.name}")
    print(f"Đóng gói {len(files)} file -> {out}")


if __name__ == "__main__":
    main()
