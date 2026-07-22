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
    ap.add_argument("--grad-accum", type=int, default=1,
                    help="effective batch = bs * grad_accum (XLM-R-large trên 12GB: bs=8, accum=2)")
    ap.add_argument("--optim", default="adamw_torch",
                    help="adamw_bnb_8bit: BẮT BUỘC cho XLM-R-large trên 12GB — Adam states fp32 "
                         "của 560M params tốn 4.5GB (model 2.2 + grad 2.2 + Adam 4.5 ≈ 9GB > vừa); "
                         "8-bit hạ Adam states còn ~1.1GB -> tổng ~7.6GB")
    ap.add_argument("--grad-ckpt", action="store_true",
                    help="gradient checkpointing: giảm activation memory, chậm ~20% (dự phòng nếu vẫn OOM)")
    ap.add_argument("--maxlen", type=int, default=256)
    ap.add_argument("--stride", type=int, default=48, help="khớp với ner_extractor lúc inference")
    ap.add_argument("--lr", type=float, default=3e-5)
    args = ap.parse_args()

    import torch
    from transformers import (AutoTokenizer, AutoModelForTokenClassification,
                              TrainingArguments, Trainer, DataCollatorForTokenClassification)
    from datasets import Dataset
    import evaluate  # seqeval wrapper (fallback dưới nếu thiếu)

    tok = AutoTokenizer.from_pretrained(args.base)

    def encode(batch):
        """Sliding window KHỚP inference (ner_extractor.py): doc dài -> nhiều cửa sổ chồng lấn.

        ⚠️ Trước đây chỉ `truncation=True` (không overflow) → doc dài hơn maxlen bị CẮT CỤT,
        mọi nhãn phía sau bị vứt + train/inference lệch nhau. Synthetic v3 dài ~1277 ký tự
        (~400 token > 256) nên bug này sẽ ăn mất ~40% nhãn nếu không sửa.
        offset_mapping của fast tokenizer luôn theo toạ độ ký tự của chuỗi GỐC, kể cả khi
        overflow → char_spans_to_token_labels dùng trực tiếp được.
        """
        enc = tok(batch["text"], truncation=True, max_length=args.maxlen, stride=args.stride,
                  return_overflowing_tokens=True, return_offsets_mapping=True)
        sample_map = enc.pop("overflow_to_sample_mapping")
        all_labels = []
        for i, offsets in enumerate(enc["offset_mapping"]):
            all_labels.append(char_spans_to_token_labels(offsets, batch["concepts"][sample_map[i]]))
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
        gradient_accumulation_steps=args.grad_accum,
        per_device_eval_batch_size=args.bs, learning_rate=args.lr,
        # warmup: XLM-R-large fine-tune KHÔNG warmup dễ collapse (loss phẳng, F1≈0)
        warmup_ratio=0.1,
        # val giờ THỰC SỰ chọn checkpoint (trước: save_strategy="no" -> val chỉ in số cho vui,
        # model lưu ra luôn là epoch cuối bất kể val nói gì)
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=1,
        load_best_model_at_end=True, metric_for_best_model="f1", greater_is_better=True,
        optim=args.optim, gradient_checkpointing=args.grad_ckpt,
        logging_steps=100, fp16=torch.cuda.is_available(), report_to=[],
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
