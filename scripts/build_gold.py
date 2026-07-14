"""Sinh gold JSON độc lập cho dev từ scripts/gold_annotations.py.

Tính position bằng cursor tuần tự trên raw (concept liệt kê theo thứ tự đọc):
- 'after': nhảy cursor tới sau anchor trước khi tìm text.
- 'occ': lấy occurrence thứ n (mặc định occurrence kế tiếp từ cursor).
Validate raw[start:end]==text; báo lỗi nếu không tìm được để sửa annotation.

Usage: python scripts/build_gold.py            # ghi ra data/labeled/ground_truth/
       python scripts/build_gold.py --check    # chỉ validate, không ghi
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.common.io_utils import read_input, write_output  # noqa: E402
from src.schema import Concept  # noqa: E402
from scripts.gold_annotations import GOLD  # noqa: E402

INPUT_DIR = ROOT / "data" / "raw" / "input"
OUT_DIR = ROOT / "data" / "labeled" / "ground_truth"


def build_file(stem, items):
    raw = read_input(INPUT_DIR / f"{stem}.txt")
    concepts = []
    cursor = 0
    errors = []
    for i, it in enumerate(items):
        text = it["t"]
        start_from = cursor
        if "after" in it:
            a = raw.find(it["after"])
            if a >= 0:
                start_from = a + len(it["after"])
        occ = it.get("occ")
        idx = -1
        if occ:
            pos = 0
            for _ in range(occ):
                idx = raw.find(text, pos)
                if idx < 0:
                    break
                pos = idx + 1
        else:
            idx = raw.find(text, start_from)
            if idx < 0:  # fallback toàn cục
                idx = raw.find(text)
        if idx < 0:
            errors.append(f"  [{stem}#{i}] NOT FOUND: {text!r}")
            continue
        end = idx + len(text)
        if raw[idx:end] != text:
            errors.append(f"  [{stem}#{i}] MISMATCH at {idx}")
            continue
        cursor = end
        concepts.append(
            Concept(text, it["y"], [idx, end], it.get("a", []), it.get("c", []))
        )
    return concepts, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not args.check:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
    total, all_errors = 0, []
    for stem, items in GOLD.items():
        concepts, errors = build_file(stem, items)
        all_errors += errors
        total += len(concepts)
        if not args.check:
            write_output(concepts, OUT_DIR / f"{stem}.json")
    print(f"Files: {len(GOLD)}, concepts: {total}, errors: {len(all_errors)}")
    for e in all_errors:
        print(e)
    if not args.check and not all_errors:
        print(f"Wrote gold -> {OUT_DIR}")


if __name__ == "__main__":
    main()
