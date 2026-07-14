# -*- coding: utf-8 -*-
"""SapBERT entity linking (Tier 1, hướng B): embedding canh chỉnh y khoa -> candidate.

SapBERT cross-lingual (XLM-R, UMLS) — discrimination tốt cho y khoa VN (khác hẳn embedder
general đã fail ở exp_0002). Encode toàn bộ tên ICD (VN+EN) + RxNorm -> FAISS IndexFlatIP,
query = span khái niệm -> cosine top-k -> mã (dedup theo code lấy sim cao nhất).

Cache embedding ra models/embeddings/ (gitignored) để build 1 lần.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from ..common.text_norm import normalize_for_match

_ROOT = Path(__file__).resolve().parent.parent.parent
_ICD = _ROOT / "knowledge_base" / "icd10" / "processed" / "icd10_vn.csv"
_RXN = _ROOT / "knowledge_base" / "rxnorm" / "processed" / "rxnorm_terms.csv"
_CACHE = _ROOT / "models" / "embeddings"
_MODEL = "cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR"


class _Encoder:
    _tok = None
    _model = None

    @classmethod
    def get(cls):
        if cls._model is None:
            import torch
            from transformers import AutoTokenizer, AutoModel
            cls._tok = AutoTokenizer.from_pretrained(_MODEL)
            cls._model = AutoModel.from_pretrained(_MODEL).eval()
            cls._dev = "cuda" if torch.cuda.is_available() else "cpu"
            cls._model.to(cls._dev)
        return cls._tok, cls._model, cls._dev

    @classmethod
    def encode(cls, texts: List[str], bs: int = 256) -> np.ndarray:
        import torch
        import torch.nn.functional as F
        tok, model, dev = cls.get()
        out = []
        for i in range(0, len(texts), bs):
            batch = [normalize_for_match(t) for t in texts[i:i + bs]]
            t = tok(batch, padding=True, truncation=True, max_length=32, return_tensors="pt").to(dev)
            with torch.no_grad():
                cls_emb = model(**t).last_hidden_state[:, 0]  # CLS
            out.append(F.normalize(cls_emb, dim=-1).cpu().numpy().astype(np.float32))
        return np.vstack(out) if out else np.zeros((0, 768), np.float32)


class SapBertIndex:
    """Index 1 nguồn (ICD hoặc RxNorm): tên -> code, embedding + FAISS."""

    def __init__(self, name: str):
        self.name = name
        self.codes: List[str] = []
        self.emb: np.ndarray = None
        self._faiss = None

    def _read(self):
        raise NotImplementedError

    def build(self, force=False) -> "SapBertIndex":
        _CACHE.mkdir(parents=True, exist_ok=True)
        cache = _CACHE / f"sapbert_{self.name}.npz"
        if cache.exists() and not force:
            d = np.load(cache, allow_pickle=True)
            self.emb = d["emb"]; self.codes = list(d["codes"])
        else:
            names, codes = self._read()
            self.emb = _Encoder.encode(names)
            self.codes = codes
            np.savez(cache, emb=self.emb, codes=np.array(codes, dtype=object))
        import faiss
        self._faiss = faiss.IndexFlatIP(self.emb.shape[1])
        self._faiss.add(self.emb)
        return self

    def query(self, text: str, k: int = 3, topn: int = 50, threshold: float = 0.5) -> List[str]:
        q = _Encoder.encode([text])
        if q.shape[0] == 0:
            return []
        sims, idx = self._faiss.search(q, topn)
        best: Dict[str, float] = {}
        for s, i in zip(sims[0], idx[0]):
            if i < 0 or s < threshold:
                continue
            c = self.codes[i]
            if s > best.get(c, -1):
                best[c] = float(s)
        ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked[:k]]


class _ICDIndex(SapBertIndex):
    def __init__(self): super().__init__("icd")
    def _read(self):
        names, codes = [], []
        with open(_ICD, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                code = (row.get("ma_benh") or "").strip()
                if not code:
                    continue
                for col in ("ten_benh_vi", "disease_name_en"):
                    nm = (row.get(col) or "").strip()
                    if nm:
                        names.append(nm); codes.append(code)
        return names, codes


class _RxnIndex(SapBertIndex):
    def __init__(self): super().__init__("rxn")
    def _read(self):
        names, codes = [], []
        with open(_RXN, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rx = (row.get("rxcui") or "").strip()
                s = (row.get("str") or "").strip()
                if rx and s:
                    names.append(s); codes.append(rx)
        return names, codes


class SapBertMatcher:
    """Duck-typed cho pipeline: match_icd / match_rxnorm (thay fuzzy KB)."""

    def __init__(self, icd_threshold=0.5, rxn_threshold=0.5, icd_k=1, rxn_k=1):
        self.icd = _ICDIndex()
        self.rxn = _RxnIndex()
        self.icd_th = icd_threshold
        self.rxn_th = rxn_threshold
        # gold thường 1 mã/khái niệm -> trả ít mã để tránh pha loãng Jaccard (dùng self.k,
        # bỏ qua k pipeline truyền vào)
        self.icd_k = icd_k
        self.rxn_k = rxn_k

    def build(self, force=False):
        self.icd.build(force=force)
        self.rxn.build(force=force)
        return self

    def match_icd(self, text: str, k: int = None) -> List[str]:
        return self.icd.query(text, k=self.icd_k, threshold=self.icd_th)

    def match_rxnorm(self, text: str, k: int = None) -> List[str]:
        return self.rxn.query(text, k=self.rxn_k, threshold=self.rxn_th)


class HybridCandidateMatcher:
    """fuzzy (KB) TRƯỚC (thắng khớp bề mặt: tăng huyết áp->I10); SapBERT LẤP khi fuzzy rỗng
    (semantic/paraphrase: hen suyễn->J45). Không để SapBERT đè fuzzy (bài học exp_0002)."""

    def __init__(self, kb, sap: SapBertMatcher):
        self.kb = kb
        self.sap = sap

    def match_icd(self, text: str, k: int = 3) -> List[str]:
        r = self.kb.match_icd(text, k=k)
        return r if r else self.sap.match_icd(text)

    def match_rxnorm(self, text: str, k: int = 1) -> List[str]:
        r = self.kb.match_rxnorm(text, k=k)
        return r if r else self.sap.match_rxnorm(text)
