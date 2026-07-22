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
    ap.add_argument("--no-split-newlines", action="store_true",
                    help="tắt _split_newlines (tái lập exp_0003; BTC cho thấy nó làm tụt text+assert)")
    ap.add_argument("--sapbert", action="store_true", help="dùng SapBERT cho candidate (thay fuzzy)")
    ap.add_argument("--hybrid", action="store_true", help="fuzzy trước, SapBERT lấp khi rỗng")
    ap.add_argument("--sap-th", type=float, default=0.5, help="ngưỡng SapBERT (cao = abstain nhiều)")
    ap.add_argument("--sapbert-model", default=None,
                    help="thư mục SapBERT fine-tuned (bỏ trống = SapBERT gốc); cache index riêng")
    ap.add_argument("--reranker", default=None,
                    help="tên/thư mục cross-encoder reranker (vd BAAI/bge-reranker-v2-m3); "
                         "dùng SapBERT retrieval + rerank thay vì lấy top-1 SapBERT trực tiếp")
    ap.add_argument("--hybrid-rerank", action="store_true",
                    help="pool ứng viên = BM25 ∪ dense (RRF) trước khi rerank (cần --reranker)")
    ap.add_argument("--icd-k", type=int, default=1, help="số mã ICD trả về/concept (gold đề có thể >1 mã)")
    ap.add_argument("--rxn-k", type=int, default=1, help="số mã RxNorm trả về/concept")
    ap.add_argument("--assertion-clf", default=None,
                    help="thư mục assertion classifier (bỏ trống = rule)")
    ap.add_argument("--dev-input", default="data/labeled/input")
    ap.add_argument("--gold", default="data/labeled/ground_truth")
    ap.add_argument("--test-input", default="data/raw_new/input")
    ap.add_argument("--desc", default="")
    args = ap.parse_args()

    exp_dir = ROOT / "experiments" / args.exp
    (exp_dir / "predictions").mkdir(parents=True, exist_ok=True)
    (exp_dir / "predictions_test").mkdir(parents=True, exist_ok=True)

    kb = KnowledgeBase().load()
    ner = None
    if args.ner:
        from src.extraction.ner_extractor import NERExtractor
        ner = NERExtractor(model_dir=args.ner, min_conf=args.min_conf,
                           split_newlines=not args.no_split_newlines).load()
        print(f"[exp] NER model: {args.ner} (min_conf={args.min_conf}, "
              f"split_newlines={not args.no_split_newlines})")
    matcher = None
    if args.reranker:
        from src.normalization.reranker import RerankMatcher, HybridRerankMatcher
        cls = HybridRerankMatcher if args.hybrid_rerank else RerankMatcher
        matcher = cls(icd_threshold=args.sap_th, rxn_threshold=args.sap_th,
                      icd_k=args.icd_k, rxn_k=args.rxn_k,
                      reranker_name=args.reranker).build()
        mode = "BM25∪dense (RRF) + RERANK" if args.hybrid_rerank else "SapBERT retrieval + RERANK"
        print(f"[exp] candidate: {mode} ({args.reranker})")
    elif args.sapbert or args.hybrid:
        from src.normalization.sapbert import SapBertMatcher, HybridCandidateMatcher
        sap = SapBertMatcher(icd_threshold=args.sap_th, rxn_threshold=args.sap_th,
                             icd_k=args.icd_k, rxn_k=args.rxn_k,
                             model_dir=args.sapbert_model).build()
        if args.sapbert_model:
            print(f"[exp] SapBERT fine-tuned: {args.sapbert_model}")
        if args.hybrid:
            matcher = HybridCandidateMatcher(kb, sap)
            print("[exp] candidate: HYBRID (fuzzy + SapBERT fallback)")
        else:
            matcher = sap
            print("[exp] candidate: SapBERT")

    clf = None
    if args.assertion_clf:
        from src.assertion.classifier import AssertionClassifier
        clf = AssertionClassifier(model_dir=args.assertion_clf).load()
        print(f"[exp] assertion: classifier {args.assertion_clf}")
    else:
        print("[exp] assertion: rule")

    # dev
    run_dir(ROOT / args.dev_input, exp_dir / "predictions", kb=kb, ner=ner, matcher=matcher,
            assertion_clf=clf)
    # test (submission)
    run_dir(ROOT / args.test_input, exp_dir / "predictions_test", kb=kb, ner=ner, matcher=matcher,
            assertion_clf=clf)

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
