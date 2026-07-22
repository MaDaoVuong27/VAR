# -*- coding: utf-8 -*-
"""Train assertion classifier đa nhãn (XLM-R) trên synthetic.

Thay rule cho isNegated/isFamily/isHistorical. Rule yếu nhất ở isHistorical (dev 60%);
classifier đọc cửa sổ ngữ cảnh + span được đánh dấu [ENT]...[/ENT].

Usage:
  python scripts/train_assertion.py --base xlm-roberta-base \
      --template data/synthetic/train.jsonl --prose data/synthetic/prose.jsonl \
      --out models/assertion_xlmr --epochs 2 --max-template 80000
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.assertion.classifier import (  # noqa: E402
    mark_context, labels_to_vec, ASSERT_LABELS, ENT_START, ENT_END,
)
from src.schema import ASSERTION_TYPES  # noqa: E402


def extract(path, limit=None):
    """(marked_context, label_vec) cho mỗi concept có-assertion-type."""
    rows = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        for c in r["concepts"]:
            if c["type"] in ASSERTION_TYPES:
                rows.append({"text": mark_context(r["text"], c["position"][0], c["position"][1]),
                             "labels": labels_to_vec(c["assertions"])})
                if limit and len(rows) >= limit:
                    return rows
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="xlm-roberta-base")
    ap.add_argument("--template", default="data/synthetic/train.jsonl")
    ap.add_argument("--prose", default="data/synthetic/prose.jsonl")
    ap.add_argument("--val-template", default="data/synthetic/val.jsonl")
    ap.add_argument("--val-prose", default="data/synthetic/prose_val.jsonl")
    ap.add_argument("--out", default="models/assertion_xlmr")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--maxlen", type=int, default=192)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-template", type=int, default=80000, help="giới hạn số example template (cân tốc độ)")
    args = ap.parse_args()

    import torch
    from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                              TrainingArguments, Trainer, DataCollatorWithPadding)
    from datasets import Dataset

    tok = AutoTokenizer.from_pretrained(args.base)
    tok.add_special_tokens({"additional_special_tokens": [ENT_START, ENT_END]})

    train_rows = extract(ROOT / args.template, args.max_template) + extract(ROOT / args.prose)
    val_rows = extract(ROOT / args.val_template, args.max_template // 10) + extract(ROOT / args.val_prose)
    print(f"train={len(train_rows)} val={len(val_rows)} example | nhãn={ASSERT_LABELS}")
    # phân bố nhãn (kiểm imbalance)
    arr = np.array([r["labels"] for r in train_rows])
    print("tỉ lệ dương mỗi nhãn:", {l: round(float(arr[:, i].mean()), 4) for i, l in enumerate(ASSERT_LABELS)})

    def encode(batch):
        enc = tok(batch["text"], truncation=True, max_length=args.maxlen)
        enc["labels"] = [[float(x) for x in lab] for lab in batch["labels"]]
        return enc

    train_ds = Dataset.from_list(train_rows).map(encode, batched=True, remove_columns=["text"])
    val_ds = Dataset.from_list(val_rows).map(encode, batched=True, remove_columns=["text"])

    model = AutoModelForSequenceClassification.from_pretrained(
        args.base, num_labels=len(ASSERT_LABELS), problem_type="multi_label_classification")
    model.resize_token_embeddings(len(tok))

    def compute_metrics(p):
        probs = 1 / (1 + np.exp(-p.predictions))
        preds = (probs >= 0.5).astype(int)
        labels = p.label_ids.astype(int)
        out = {}
        for i, l in enumerate(ASSERT_LABELS):
            tp = int(((preds[:, i] == 1) & (labels[:, i] == 1)).sum())
            fp = int(((preds[:, i] == 1) & (labels[:, i] == 0)).sum())
            fn = int(((preds[:, i] == 0) & (labels[:, i] == 1)).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            out[f"f1_{l}"] = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out["f1_macro"] = float(np.mean([out[f"f1_{l}"] for l in ASSERT_LABELS]))
        return out

    targs = TrainingArguments(
        output_dir=str(ROOT / args.out / "_ckpt"),
        num_train_epochs=args.epochs, per_device_train_batch_size=args.bs,
        per_device_eval_batch_size=args.bs, learning_rate=args.lr, warmup_ratio=0.1,
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=1,
        load_best_model_at_end=True, metric_for_best_model="f1_macro", greater_is_better=True,
        logging_steps=200, fp16=torch.cuda.is_available(), report_to=[],
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds,
                      data_collator=DataCollatorWithPadding(tok), compute_metrics=compute_metrics)
    trainer.train()
    print("EVAL:", trainer.evaluate())
    outdir = ROOT / args.out
    model.save_pretrained(outdir)
    tok.save_pretrained(outdir)
    print(f"Saved assertion classifier -> {outdir}")


if __name__ == "__main__":
    main()
