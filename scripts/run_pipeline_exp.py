# -*- coding: utf-8 -*-
"""Chạy 1 experiment: pipeline trên dev + test, eval dev, đóng gói output.zip, lưu metrics.

Usage:
  # baseline rule (mặc định)
  python scripts/run_pipeline_exp.py --exp exp_0003_ner --ner models/ner_xlmr
  # không NER (rule)
  python scripts/run_pipeline_exp.py --exp exp_xxx
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.normalization import KnowledgeBase  # noqa: E402
from src.pipeline import run_dir  # noqa: E402
from src.common.io_utils import load_gold_dir, read_gold  # noqa: E402
from src.eval.metric import score_dataset  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True, help="tên folder experiment")
    ap.add_argument("--ner", default=None, help="thư mục model NER (bỏ trống = rule)")
    ap.add_argument("--min-conf", type=float, default=0.6, help="ngưỡng confidence NER")
    ap.add_argument("--sapbert", action="store_true", help="dùng SapBERT cho candidate (thay fuzzy)")
    ap.add_argument("--hybrid", action="store_true", help="fuzzy trước, SapBERT lấp khi rỗng")
    ap.add_argument("--sap-th", type=float, default=0.5, help="ngưỡng SapBERT (cao = abstain nhiều)")
    ap.add_argument("--dev-input", default="data/labeled/input")
    ap.add_argument("--gold", default="data/labeled/ground_truth")
    ap.add_argument("--test-input", default="data/raw/input")
    ap.add_argument("--desc", default="")
    args = ap.parse_args()

    exp_dir = ROOT / "experiments" / args.exp
    (exp_dir / "predictions").mkdir(parents=True, exist_ok=True)
    (exp_dir / "predictions_test").mkdir(parents=True, exist_ok=True)

    kb = KnowledgeBase().load()
    ner = None
    if args.ner:
        from src.extraction.ner_extractor import NERExtractor
        ner = NERExtractor(model_dir=args.ner, min_conf=args.min_conf).load()
        print(f"[exp] NER model: {args.ner} (min_conf={args.min_conf})")
    matcher = None
    if args.sapbert or args.hybrid:
        from src.normalization.sapbert import SapBertMatcher, HybridCandidateMatcher
        sap = SapBertMatcher(icd_threshold=args.sap_th, rxn_threshold=args.sap_th).build()
        if args.hybrid:
            matcher = HybridCandidateMatcher(kb, sap)
            print("[exp] candidate: HYBRID (fuzzy + SapBERT fallback)")
        else:
            matcher = sap
            print("[exp] candidate: SapBERT")

    # dev
    run_dir(ROOT / args.dev_input, exp_dir / "predictions", kb=kb, ner=ner, matcher=matcher)
    # test (submission)
    run_dir(ROOT / args.test_input, exp_dir / "predictions_test", kb=kb, ner=ner, matcher=matcher)

    # eval dev
    golds = load_gold_dir(ROOT / args.gold)
    preds = {}
    for stem in golds:
        p = exp_dir / "predictions" / f"{stem}.json"
        preds[stem] = read_gold(p) if p.exists() else []
    scores = score_dataset(preds, golds)
    print("\n=== DEV scores (" + str(len(golds)) + " file) ===")
    print(json.dumps(scores.as_dict(), ensure_ascii=False, indent=2))

    # đóng gói output.zip
    zip_path = exp_dir / "output.zip"
    tests = sorted((exp_dir / "predictions_test").glob("*.json"),
                   key=lambda p: (len(p.stem), p.stem))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in tests:
            zf.write(p, arcname=f"output/{p.name}")

    (exp_dir / "metrics.json").write_text(json.dumps({
        "exp": args.exp, "desc": args.desc, "ner": args.ner,
        "dev_scores": scores.as_dict(), "n_dev": len(golds),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote submission -> {zip_path}")
    print(f"Wrote metrics -> {exp_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()
