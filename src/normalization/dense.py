"""Dense retrieval cho candidate mapping (Tier 1) — embedding đa ngôn ngữ + cosine.

Bù cho lexical: bắt paraphrase/đồng nghĩa VN mà token match bỏ lỡ (vd 'hen suyễn' vs
tên ICD 'Hen'). Model nhỏ (~118M, trong ngân sách 9B tổng), chạy GPU, embedding KB được
cache ra models/embeddings/ (gitignored) để không encode lại mỗi lần.

HybridMatcher: hợp nhất điểm lexical (RapidFuzz, đã có trong KB) + dense (cosine) → top-k.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..common.text_norm import normalize_for_match

_ROOT = Path(__file__).resolve().parent.parent.parent
_ICD_CSV = _ROOT / "knowledge_base" / "icd10" / "processed" / "icd10_vn.csv"
_CACHE = _ROOT / "models" / "embeddings"
_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class DenseICD:
    """Index dense cho tên bệnh ICD (cả cột VN + EN)."""

    def __init__(self, model_name: str = _MODEL, csv_path=_ICD_CSV):
        self.model_name = model_name
        self.csv_path = Path(csv_path)
        self.names: List[str] = []
        self.codes: List[str] = []
        self.emb: Optional[np.ndarray] = None  # (N, d) đã chuẩn hoá L2
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import torch
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = SentenceTransformer(self.model_name, device=dev)
        return self._model

    def _read_names(self):
        names, codes = [], []
        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                code = (row.get("ma_benh") or "").strip()
                if not code:
                    continue
                for col in ("ten_benh_vi", "disease_name_en"):
                    nm = (row.get(col) or "").strip()
                    if nm:
                        names.append(nm)
                        codes.append(code)
        self.names, self.codes = names, codes

    def build(self, force: bool = False) -> "DenseICD":
        _CACHE.mkdir(parents=True, exist_ok=True)
        cache = _CACHE / "icd_minilm.npz"
        if cache.exists() and not force:
            data = np.load(cache, allow_pickle=True)
            self.emb = data["emb"]
            self.codes = list(data["codes"])
            self.names = list(data["names"])
            return self
        self._read_names()
        model = self._load_model()
        self.emb = model.encode(
            [normalize_for_match(n) for n in self.names],
            batch_size=256, normalize_embeddings=True, show_progress_bar=False,
        ).astype(np.float32)
        np.savez(cache, emb=self.emb, codes=np.array(self.codes, dtype=object),
                 names=np.array(self.names, dtype=object))
        return self

    def query(self, text: str, k: int = 5, threshold: float = 0.6) -> List[tuple]:
        """Trả [(code, cosine)] top-k theo mã (gộp trùng lấy max)."""
        model = self._load_model()
        q = model.encode([normalize_for_match(text)], normalize_embeddings=True)[0].astype(np.float32)
        sims = self.emb @ q  # cosine vì đã chuẩn hoá
        idx = np.argsort(-sims)[: k * 6]
        best: Dict[str, float] = {}
        for i in idx:
            s = float(sims[i])
            if s < threshold:
                break
            c = self.codes[i]
            if s > best.get(c, 0):
                best[c] = s
        return sorted(best.items(), key=lambda x: x[1], reverse=True)[:k]


class HybridMatcher:
    """Ghép lexical (KB) + dense (ICD) cho candidate. Drug giữ lexical (đã tốt)."""

    def __init__(self, kb, dense_icd: DenseICD, dense_weight: float = 1.0):
        self.kb = kb
        self.dense = dense_icd
        self.dense_weight = dense_weight

    def match_icd(self, text: str, k: int = 3) -> List[str]:
        # lexical (điểm 0-100 -> 0-1) + dense (cosine 0-1), gộp theo mã lấy max
        scores: Dict[str, float] = {}
        for code in self.kb.match_icd(text, k=k * 2):
            scores[code] = max(scores.get(code, 0), 0.75)  # lexical hit: coi ~0.75
        for code, cos in self.dense.query(text, k=k * 2):
            scores[code] = max(scores.get(code, 0), cos * self.dense_weight)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked[:k]]

    def match_rxnorm(self, text: str, k: int = 1) -> List[str]:
        return self.kb.match_rxnorm(text, k=k)
