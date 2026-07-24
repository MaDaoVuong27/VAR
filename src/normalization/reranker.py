# -*- coding: utf-8 -*-
"""Cross-encoder reranker cho candidate mapping (khối B, bước sau SapBERT retrieval).

Ý tưởng: SapBERT (bi-encoder) đã tìm đúng VÙNG ứng viên nhưng đôi khi chọn nhầm mã cụ thể
giữa các ứng viên gần nhau (đo được: 'suy tim' -> F20.2 tâm thần phân liệt thay vì mã tim
mạch đúng). Cross-encoder chấm riêng từng cặp (span, tên_ứng_viên) — tốn hơn bi-encoder
nhưng chính xác hơn vì thấy được tương tác 2 chiều giữa 2 chuỗi, không chỉ khoảng cách vector.

KHÔNG đụng ngưỡng abstain của SapBERT (đã tinh trên th=0.7): reranker chỉ ĐỔI THỨ TỰ trong
tập ứng viên mà SapBERT đã chấp nhận, không quyết định có abstain hay không. Tách bạch
"tìm ứng viên" (SapBERT, đang ổn) khỏi "chọn mã cuối" (chỗ đang sai).

2 chế độ:
- off-the-shelf: BAAI/bge-reranker-v2-m3 (568M, đã cache) — sanity check nhanh, KHÔNG train.
- fine-tuned: checkpoint tự train (cross-encoder nhỏ hơn, mMiniLM ~118M) — nếu off-the-shelf
  cho tín hiệu tốt mới đáng đầu tư train riêng đúng ngân sách.
"""
from __future__ import annotations

import csv
from typing import Dict, List, Optional, Tuple

import numpy as np

from .sapbert import _ICDIndex, _RxnIndex, _Encoder, _ICD, _RXN
from ..common.text_norm import normalize_for_match


def build_icd_descriptions() -> Dict[str, str]:
    """Mô tả mã ICD dựng RULE THUẦN từ chính KB — KHÔNG cần LLM (xem
    docs/TRAINING_WORKFLOW_PLAN.md §C1). Độ phủ đã đo: ten_benh_vi/disease_name_en/
    ten_nhom_3ky_tu_vi/ten_khoi_vi/ten_chuong_vi = 100%, huong_dan_bo_sung_vi (đồng nghĩa) = 40%.
    """
    desc: Dict[str, str] = {}
    with open(_ICD, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("ma_benh") or "").strip()
            if not code or code in desc:
                continue
            vi = (row.get("ten_benh_vi") or "").strip()
            en = (row.get("disease_name_en") or "").strip()
            syn = (row.get("huong_dan_bo_sung_vi") or "").strip()
            grp = (row.get("ten_nhom_3ky_tu_vi") or "").strip()
            blk = (row.get("ten_khoi_vi") or "").strip()
            chap = (row.get("ten_chuong_vi") or "").strip()
            if not vi and not en:
                continue
            parts = [vi or en]
            if syn:
                parts.append(f"(còn gọi: {syn})")
            if grp or blk or chap:
                parts.append(f"Thuộc nhóm {grp}, khối {blk}, chương {chap}.")
            if en and vi:
                parts.append(f"Tên tiếng Anh: {en}.")
            desc[code] = " ".join(p for p in parts if p)
    return desc


def build_rxnorm_descriptions() -> Dict[str, str]:
    """Mô tả mã RxNorm từ TÊN ĐA DẠNG cùng rxcui (IN/SCD/SBD/SY/PSN/TMSY...) — 31% rxcui có
    >1 TTY, dùng làm 'đồng nghĩa' miễn phí (xem docs/TRAINING_WORKFLOW_PLAN.md §C1)."""
    variants: Dict[str, List[str]] = {}
    with open(_RXN, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rx = (row.get("rxcui") or "").strip()
            s = (row.get("str") or "").strip()
            if rx and s:
                variants.setdefault(rx, [])
                if s not in variants[rx]:
                    variants[rx].append(s)
    desc: Dict[str, str] = {}
    for rx, names in variants.items():
        primary, others = names[0], names[1:3]
        desc[rx] = f"{primary}. Còn gọi: {'; '.join(others)}." if others else primary
    return desc


class _CrossEncoder:
    _tok = None
    _model = None
    _name = None

    @classmethod
    def get(cls, name: str):
        if cls._model is None or cls._name != name:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            cls._tok = AutoTokenizer.from_pretrained(name)
            cls._model = AutoModelForSequenceClassification.from_pretrained(name).eval()
            cls._dev = "cuda" if torch.cuda.is_available() else "cpu"
            cls._model.to(cls._dev)
            cls._name = name
        return cls._tok, cls._model, cls._dev

    @classmethod
    def score(cls, name: str, query: str, passages: List[str], max_length: int = 64) -> List[float]:
        import torch
        tok, model, dev = cls.get(name)
        pairs = [[query, p] for p in passages]
        enc = tok(pairs, padding=True, truncation=True, max_length=max_length,
                  return_tensors="pt").to(dev)
        with torch.no_grad():
            logits = model(**enc).logits.view(-1).float()
        return logits.cpu().tolist()


def _topk_with_names(index, text: str, threshold: float, topn: int = 10) -> List[Tuple[str, str, float]]:
    """Top ứng viên (code, name, sim) từ 1 SapBertIndex, dedup theo code (giữ tên sim cao nhất)."""
    q = _Encoder.encode([text])
    if q.shape[0] == 0:
        return []
    sims, idx = index._faiss.search(q, topn)
    best: Dict[str, Tuple[str, float]] = {}
    for s, i in zip(sims[0], idx[0]):
        if i < 0 or s < threshold:
            continue
        c = index.codes[i]
        nm = index.names[i] if getattr(index, "names", None) else c
        if c not in best or s > best[c][1]:
            best[c] = (nm, float(s))
    ranked = sorted(((c, nm, s) for c, (nm, s) in best.items()), key=lambda x: x[2], reverse=True)
    return ranked


class _BM25Index:
    """BM25 lexical index trên cùng corpus tên với SapBERT (dedup theo code lúc query)."""

    def __init__(self, sap_index):
        self.names = sap_index.names          # song song sap_index.codes
        self.codes = sap_index.codes
        self._bm = None

    def build(self):
        from rank_bm25 import BM25Okapi
        toks = [normalize_for_match(n).split() for n in self.names]
        self._bm = BM25Okapi(toks)
        return self

    def topk(self, text: str, topn: int = 10) -> List[Tuple[str, str, float]]:
        q = normalize_for_match(text).split()
        if not q:
            return []
        scores = self._bm.get_scores(q)
        top = np.argsort(scores)[::-1][:topn]
        out, seen = [], set()
        for i in top:
            if scores[i] <= 0:
                continue
            c = self.codes[i]
            if c in seen:
                continue
            seen.add(c)
            out.append((c, self.names[i], float(scores[i])))
        return out


def _rrf_fuse(dense: List[Tuple[str, str, float]], bm25: List[Tuple[str, str, float]],
              k: int = 60) -> List[Tuple[str, str]]:
    """Reciprocal Rank Fusion: hợp nhất 2 danh sách theo THỨ HẠNG (không trộn thang điểm).

    Tránh lỗi đã giết exp_0002: BM25 score (~10-18) và cosine (~0.7) khác thang tuyệt đối →
    cộng thẳng thì 1 nguồn đè nguồn kia. RRF chỉ dùng rank: score = Σ 1/(k+rank).
    Giữ tên đại diện của mỗi code (ưu tiên tên xuất hiện ở rank cao nhất bất kỳ nguồn nào).
    """
    agg: Dict[str, float] = {}
    name_of: Dict[str, Tuple[int, str]] = {}  # code -> (best_rank, name)
    for lst in (dense, bm25):
        for rank, (code, name, _score) in enumerate(lst):
            agg[code] = agg.get(code, 0.0) + 1.0 / (k + rank)
            if code not in name_of or rank < name_of[code][0]:
                name_of[code] = (rank, name)
    ranked = sorted(agg.items(), key=lambda x: x[1], reverse=True)
    return [(code, name_of[code][1]) for code, _ in ranked]


class RerankMatcher:
    """Duck-typed cho pipeline: match_icd/match_rxnorm. SapBERT retrieval + cross-encoder rerank."""

    def __init__(self, icd_threshold=0.7, rxn_threshold=0.7, icd_k=1, rxn_k=1,
                 reranker_name="BAAI/bge-reranker-v2-m3", topn=10, use_description=False):
        self.icd = _ICDIndex()
        self.rxn = _RxnIndex()
        self.icd_th = icd_threshold
        self.rxn_th = rxn_threshold
        self.icd_k = icd_k
        self.rxn_k = rxn_k
        self.reranker_name = reranker_name
        self.topn = topn
        self.use_description = use_description
        self.icd_desc: Dict[str, str] = {}
        self.rxn_desc: Dict[str, str] = {}

    def build(self, force=False):
        self.icd.build(force=force)
        self.rxn.build(force=force)
        # names không có trong cache npz (chỉ emb+codes) -> đọc lại CSV (rẻ, chỉ text)
        # để dedup-theo-code khớp đúng thứ tự với self.codes đã build.
        n, c = self.icd._read()
        assert c == self.icd.codes, "thứ tự _read() phải khớp cache — CSV không được đổi giữa 2 lần"
        self.icd.names = n
        n2, c2 = self.rxn._read()
        assert c2 == self.rxn.codes
        self.rxn.names = n2
        if self.use_description:
            # Mô tả RULE THUẦN từ KB (§C1 TRAINING_WORKFLOW_PLAN.md) — cross-encoder thấy
            # phân cấp/đồng nghĩa thay vì chỉ 1 tên trần, giúp phân biệt mã gần nghĩa
            # ("suy thận cấp" vs "suy thận mạn" nằm khác nhóm 3 ký tự).
            self.icd_desc = build_icd_descriptions()
            self.rxn_desc = build_rxnorm_descriptions()
        _CrossEncoder.get(self.reranker_name)  # nạp trước, tránh lazy-load lệch lúc đo thời gian
        return self

    def _match(self, index, text: str, th: float, k: int, desc_map: Dict[str, str]) -> List[str]:
        cands = _topk_with_names(index, text, th, self.topn)
        if not cands:
            return []
        if len(cands) == 1:
            return [cands[0][0]]
        passages = [desc_map.get(code, nm) for code, nm, _ in cands]
        # mô tả KB dài hơn tên trần -> max_length=64 cắt cụt phần phân cấp/đồng nghĩa ở cuối
        # câu (đã đo: max_length=64 làm dev cand TỆ HƠN 0.3333->0.3011). 160 đủ cho mô tả dài
        # nhất mà không tốn quá nhiều so với 64.
        maxlen = 160 if self.use_description else 64
        scores = _CrossEncoder.score(self.reranker_name, text, passages, max_length=maxlen)
        order = sorted(zip(cands, scores), key=lambda x: x[1], reverse=True)
        return [c for (c, _, _), _ in order[:k]]

    def match_icd(self, text: str, k: int = None) -> List[str]:
        return self._match(self.icd, text, self.icd_th, self.icd_k, self.icd_desc)

    def match_rxnorm(self, text: str, k: int = None) -> List[str]:
        return self._match(self.rxn, text, self.rxn_th, self.rxn_k, self.rxn_desc)


class HybridRerankMatcher(RerankMatcher):
    """Hybrid BM25 + dense (RRF) → cross-encoder rerank.

    Khác RerankMatcher: pool ứng viên cho reranker = dense(SapBERT) ∪ BM25(lexical), hợp nhất
    bằng RRF. Reranker thấy cả match ngữ nghĩa VN lẫn match từ vựng/exact (tên thuốc EN, mã).

    ⚠️ ABSTAIN GATE GIỮ NGUYÊN theo dense (bài học exp_0002/0012: retrieval luôn-trả-mã phá
    abstain → tụt điểm). BM25 CHỈ làm giàu pool khi dense đã vượt threshold (không abstain);
    KHÔNG cứu span mà dense abstain (giữ hành vi abstain đã chứng minh tốt).
    """

    def __init__(self, *args, bm25_topn=10, **kwargs):
        super().__init__(*args, **kwargs)
        self.bm25_topn = bm25_topn
        self.icd_bm = None
        self.rxn_bm = None

    def build(self, force=False):
        super().build(force=force)
        self.icd_bm = _BM25Index(self.icd).build()
        self.rxn_bm = _BM25Index(self.rxn).build()
        return self

    def _match_hybrid(self, index, bm25, text: str, th: float, k: int) -> List[str]:
        # 1. Dense retrieval + ABSTAIN GATE (giữ nguyên: dense top < th → rỗng)
        dense = _topk_with_names(index, text, th, self.topn)
        if not dense:
            return []
        # 2. BM25 làm giàu pool (chỉ khi KHÔNG abstain)
        bm_hits = bm25.topk(text, self.bm25_topn)
        # 3. RRF hợp nhất theo rank (không trộn thang điểm)
        fused = _rrf_fuse(dense, bm_hits)
        if len(fused) == 1:
            return [fused[0][0]]
        # 4. Cross-encoder rerank pool hợp nhất
        names = [nm for _, nm in fused]
        scores = _CrossEncoder.score(self.reranker_name, text, names)
        order = sorted(zip(fused, scores), key=lambda x: x[1], reverse=True)
        return [c for (c, _), _ in order[:k]]

    def match_icd(self, text: str, k: int = None) -> List[str]:
        return self._match_hybrid(self.icd, self.icd_bm, text, self.icd_th, self.icd_k)

    def match_rxnorm(self, text: str, k: int = None) -> List[str]:
        return self._match_hybrid(self.rxn, self.rxn_bm, text, self.rxn_th, self.rxn_k)
