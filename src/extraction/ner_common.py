# -*- coding: utf-8 -*-
"""Dùng chung cho train + inference NER: nhãn BIO 5 type, căn char-span <-> token, decode."""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..schema import (
    TYPE_CHAN_DOAN, TYPE_KQ_XN, TYPE_TEN_XN, TYPE_THUOC, TYPE_TRIEU_CHUNG,
)

TYPES = [TYPE_TRIEU_CHUNG, TYPE_TEN_XN, TYPE_KQ_XN, TYPE_CHAN_DOAN, TYPE_THUOC]

LABELS = ["O"] + [f"{p}-{t}" for t in TYPES for p in ("B", "I")]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}


def char_spans_to_token_labels(offsets: List[Tuple[int, int]], concepts: List[dict]) -> List[int]:
    """offsets: offset_mapping của tokenizer (list (start,end)). concepts: [{position:[s,e],type}].
    Trả list label-id cho từng token (-100 cho special/subword-pad token start==end)."""
    labels = []
    spans = sorted(([c["position"][0], c["position"][1], c["type"]] for c in concepts),
                   key=lambda x: x[0])
    for (ts, te) in offsets:
        if ts == te:  # special token
            labels.append(-100)
            continue
        lab = "O"
        for es, ee, typ in spans:
            if ts < ee and te > es:  # overlap
                lab = f"{'B' if ts <= es else 'I'}-{typ}"
                break
        labels.append(LABEL2ID[lab])
    return labels


def token_labels_to_char_spans(offsets: List[Tuple[int, int]], label_ids: List[int],
                               probs: List[float] = None) -> List[dict]:
    """Decode chuỗi nhãn token -> list span ký tự {type, position, conf}.
    probs (tùy chọn): max-softmax mỗi token -> conf span = trung bình prob các token."""
    spans = []
    cur_type = cur_start = cur_end = None
    cur_probs: List[float] = []

    def flush():
        nonlocal cur_type, cur_start, cur_end, cur_probs
        if cur_type is not None:
            conf = sum(cur_probs) / len(cur_probs) if cur_probs else 1.0
            spans.append({"type": cur_type, "position": [cur_start, cur_end], "conf": conf})
        cur_type, cur_start, cur_end, cur_probs = None, None, None, []

    for i, ((ts, te), lid) in enumerate(zip(offsets, label_ids)):
        if ts == te:
            continue
        lab = ID2LABEL.get(lid, "O")
        p = probs[i] if probs is not None else 1.0
        if lab == "O":
            flush()
            continue
        prefix, typ = lab.split("-", 1)
        if prefix == "B" or typ != cur_type:
            flush()
            cur_type, cur_start, cur_end, cur_probs = typ, ts, te, [p]
        else:
            cur_end = te
            cur_probs.append(p)
    flush()
    return spans
