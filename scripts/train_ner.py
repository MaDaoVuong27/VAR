# -*- coding: utf-8 -*-
"""Train NER token-classification (XLM-R) trên synthetic data.

Usage:
  python scripts/train_ner.py --base xlm-roberta-base \
      --train data/synthetic/train.jsonl --val data/synthetic/val.jsonl \
      --out models/ner_xlmr --epochs 3 --bs 16 --maxlen 256
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.extraction.ner_common import (  # noqa: E402
    LABELS, LABEL2ID, ID2LABEL, char_spans_to_token_labels,
)


def load_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="xlm-roberta-base")
    ap.add_argument("--train", default="data/synthetic/train.jsonl")
    ap.add_argument("--val", default="data/synthetic/val.jsonl")
    ap.add_argument("--out", default="models/ner_xlmr")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--maxlen", type=int, default=256)
    ap.add_argument("--lr", type=float, default=3e-5)
    args = ap.parse_args()

    import torch
    from transformers import (AutoTokenizer, AutoModelForTokenClassification,
                              TrainingArguments, Trainer, DataCollatorForTokenClassification)
    from datasets import Dataset
    import evaluate  # seqeval wrapper (fallback dưới nếu thiếu)

    tok = AutoTokenizer.from_pretrained(args.base)

    def encode(batch):
        enc = tok(batch["text"], truncation=True, max_length=args.maxlen,
                  return_offsets_mapping=True)
        all_labels = []
        for i, offsets in enumerate(enc["offset_mapping"]):
            all_labels.append(char_spans_to_token_labels(offsets, batch["concepts"][i]))
        enc["labels"] = all_labels
        enc.pop("offset_mapping")
        return enc

    train_ds = Dataset.from_list(load_jsonl(ROOT / args.train)).map(
        encode, batched=True, remove_columns=["text", "concepts"])
    val_ds = Dataset.from_list(load_jsonl(ROOT / args.val)).map(
        encode, batched=True, remove_columns=["text", "concepts"])

    model = AutoModelForTokenClassification.from_pretrained(
        args.base, num_labels=len(LABELS), id2label=ID2LABEL, label2id=LABEL2ID)

    try:
        seqeval = evaluate.load("seqeval")
    except Exception:
        seqeval = None

    def compute_metrics(p):
        preds = np.argmax(p.predictions, axis=2)
        true_lab, pred_lab = [], []
        for pred, lab in zip(preds, p.label_ids):
            tl, pl = [], []
            for pi, li in zip(pred, lab):
                if li == -100:
                    continue
                tl.append(ID2LABEL[li]); pl.append(ID2LABEL[pi])
            true_lab.append(tl); pred_lab.append(pl)
        if seqeval is None:
            return {}
        r = seqeval.compute(predictions=pred_lab, references=true_lab, zero_division=0)
        return {"f1": r["overall_f1"], "precision": r["overall_precision"],
                "recall": r["overall_recall"]}

    targs = TrainingArguments(
        output_dir=str(ROOT / args.out / "_ckpt"),
        num_train_epochs=args.epochs, per_device_train_batch_size=args.bs,
        per_device_eval_batch_size=args.bs, learning_rate=args.lr,
        eval_strategy="epoch", save_strategy="no", logging_steps=100,
        fp16=torch.cuda.is_available(), report_to=[],
    )
    trainer = Trainer(
        model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds,
        data_collator=DataCollatorForTokenClassification(tok),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    print("EVAL:", trainer.evaluate())
    outdir = ROOT / args.out
    model.save_pretrained(outdir)
    tok.save_pretrained(outdir)
    print(f"Saved NER model -> {outdir}")


if __name__ == "__main__":
    main()
