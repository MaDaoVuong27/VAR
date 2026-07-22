# -*- coding: utf-8 -*-
"""Assertion classifier (multi-label) — thay rule cho isNegated/isFamily/isHistorical.

Bối cảnh (đo trên dev gold): rule hiện tại đúng isNegated 97%, isFamily 97%, nhưng
isHistorical CHỈ 60% — mà isHistorical là loại NHIỀU nhất (43% concept có-assertion). Rule
dò cue theo từng DÒNG nên bỏ sót tiền sử diễn đạt trong văn xuôi. Classifier đọc cửa sổ
ngữ cảnh quanh span → bắt được cue xa/tinh tế hơn.

Kiến trúc: XLM-R-base, đánh dấu span bằng token đặc biệt [ENT]...[/ENT] trong cửa sổ ngữ
cảnh → biểu diễn [CLS] → 3 đầu sigmoid (đa nhãn, mỗi assertion độc lập 0/1).

Dùng chung train + inference: hàm `mark_context` phải khớp tuyệt đối 2 phía.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..schema import ASSERT_NEGATED, ASSERT_FAMILY, ASSERT_HISTORICAL, ASSERTION_TYPES

_ROOT = Path(__file__).resolve().parent.parent.parent

# thứ tự nhãn cố định cho vector đa nhãn
ASSERT_LABELS = [ASSERT_NEGATED, ASSERT_FAMILY, ASSERT_HISTORICAL]
ENT_START, ENT_END = "[ENT]", "[/ENT]"

# cửa sổ ngữ cảnh quanh span (ký tự) — đủ để bắt cue tiền sử đứng đầu câu/đoạn
CTX_BEFORE = 180
CTX_AFTER = 80


def mark_context(raw: str, start: int, end: int) -> str:
    """Trả cửa sổ ngữ cảnh quanh [start,end) với span được bọc [ENT]...[/ENT].

    Cửa sổ cắt theo ký tự rồi snap về biên khoảng trắng gần nhất để không cắt giữa từ.
    """
    lo = max(0, start - CTX_BEFORE)
    hi = min(len(raw), end + CTX_AFTER)
    # snap biên trái/phải về khoảng trắng để không cụt từ (trừ khi chạm đầu/cuối)
    if lo > 0:
        sp = raw.find(" ", lo, start)
        if sp != -1:
            lo = sp + 1
    if hi < len(raw):
        sp = raw.rfind(" ", end, hi)
        if sp != -1:
            hi = sp
    return raw[lo:start] + f" {ENT_START} " + raw[start:end] + f" {ENT_END} " + raw[end:hi]


def labels_to_vec(assertions: List[str]) -> List[float]:
    s = set(assertions or [])
    return [1.0 if lab in s else 0.0 for lab in ASSERT_LABELS]


def vec_to_labels(vec, threshold: float = 0.5) -> List[str]:
    return [lab for lab, v in zip(ASSERT_LABELS, vec) if v >= threshold]


class AssertionClassifier:
    """Inference: gán assertion cho list mention tại chỗ (thay assign_assertions)."""

    def __init__(self, model_dir="models/assertion_xlmr", batch_size: int = 32,
                 threshold: float = 0.5):
        self.model_dir = str(_ROOT / model_dir) if not Path(model_dir).is_absolute() else model_dir
        self.batch_size = batch_size
        self.threshold = threshold
        self._tok = None
        self._model = None
        self._device = None

    def load(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        self._tok = AutoTokenizer.from_pretrained(self.model_dir)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self._device).eval()
        return self

    def assign(self, raw: str, mentions: List) -> None:
        """Gán m.assertions tại chỗ. Mention không thuộc ASSERTION_TYPES -> []."""
        import torch
        targets = [m for m in mentions if m.type in ASSERTION_TYPES]
        for m in mentions:
            if m.type not in ASSERTION_TYPES:
                m.assertions = []
        if not targets:
            return
        ctxs = [mark_context(raw, m.start, m.end) for m in targets]
        for i in range(0, len(ctxs), self.batch_size):
            batch = ctxs[i:i + self.batch_size]
            enc = self._tok(batch, truncation=True, max_length=192, padding=True,
                            return_tensors="pt").to(self._device)
            with torch.no_grad():
                probs = torch.sigmoid(self._model(**enc).logits).cpu().tolist()
            for m, p in zip(targets[i:i + self.batch_size], probs):
                m.assertions = vec_to_labels(p, self.threshold)
