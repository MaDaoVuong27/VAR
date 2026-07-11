"""Knowledge base ICD-10 (Bộ Y tế) + RxNorm: nạp + so khớp tên -> mã (candidates).

Chiến lược matching (xem docs/EDA_FINDINGS.md §5):
- ICD-10: khớp span chẩn đoán với **cả 2 cột** ten_benh_vi (VN) + disease_name_en (EN)
  → 2 cột bù nhau, tăng recall. Exact normalized trước, rồi fuzzy top-k.
- RxNorm: block theo token đầu (tên hoạt chất/brand) rồi fuzzy trong block → nhanh.
- Có ngưỡng điểm: dưới ngưỡng trả rỗng (tránh phạt candidate sai trên false-positive).

Chạy hoàn toàn offline, chỉ dùng CSV trong knowledge_base/*/processed/ (không model ML).
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from ..common.text_norm import normalize_for_match

_ROOT = Path(__file__).resolve().parent.parent.parent
_ICD_CSV = _ROOT / "knowledge_base" / "icd10" / "processed" / "icd10_vn.csv"
_RXN_CSV = _ROOT / "knowledge_base" / "rxnorm" / "processed" / "rxnorm_terms.csv"

_ALPHA = re.compile(r"[a-zà-ỹ]{2,}", re.IGNORECASE)


def _head_token(norm: str) -> Optional[str]:
    """Token chữ đầu tiên (>=2 ký tự) làm khoá block cho RxNorm."""
    m = _ALPHA.search(norm)
    return m.group(0) if m else None


class KnowledgeBase:
    def __init__(self, icd_csv=_ICD_CSV, rxn_csv=_RXN_CSV):
        self.icd_csv = Path(icd_csv)
        self.rxn_csv = Path(rxn_csv)
        # ICD
        self._icd_exact: Dict[str, set] = defaultdict(set)      # norm name -> {code}
        self._icd_names: List[str] = []                          # norm name list (fuzzy)
        self._icd_name_codes: List[str] = []                     # code song song _icd_names
        # RxNorm
        self._rxn_exact: Dict[str, set] = defaultdict(set)       # norm str -> {rxcui}
        self._rxn_block: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # head -> [(norm,rxcui)]
        self.drug_vocab: set = set()   # tên thuốc 1 token (ingredient/brand) để nhận diện THUỐC
        self._loaded = False

    # ---------- load ----------
    def load(self) -> "KnowledgeBase":
        if self._loaded:
            return self
        self._load_icd()
        self._load_rxn()
        self._loaded = True
        return self

    def _load_icd(self):
        with open(self.icd_csv, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                code = (row.get("ma_benh") or "").strip()
                if not code:
                    continue
                for col in ("ten_benh_vi", "disease_name_en"):
                    name = (row.get(col) or "").strip()
                    if not name:
                        continue
                    norm = normalize_for_match(name)
                    if not norm:
                        continue
                    self._icd_exact[norm].add(code)
                    self._icd_names.append(norm)
                    self._icd_name_codes.append(code)

    def _load_rxn(self):
        with open(self.rxn_csv, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rxcui = (row.get("rxcui") or "").strip()
                s = (row.get("str") or "").strip()
                if not rxcui or not s:
                    continue
                norm = normalize_for_match(s)
                if not norm:
                    continue
                self._rxn_exact[norm].add(rxcui)
                head = _head_token(norm)
                if head:
                    self._rxn_block[head].append((norm, rxcui))
                # vocab tên thuốc 1 token (ingredient/brand) — bỏ token quá ngắn/gây nhiễu
                if " " not in norm and norm.isalpha() and len(norm) >= 4:
                    self.drug_vocab.add(norm)

    def is_drug_name(self, token: str) -> bool:
        return normalize_for_match(token) in self.drug_vocab

    # ---------- match ----------
    def match_icd(self, text: str, k: int = 3, threshold: int = 78) -> List[str]:
        """Trả top-k mã ICD cho 1 span chẩn đoán (rỗng nếu không đủ tin cậy).

        token_set_ratio: mạnh cho tên bệnh VN (span thường là tập con của tên ICD dài).
        """
        norm = normalize_for_match(text)
        if not norm:
            return []
        if norm in self._icd_exact:
            return list(self._icd_exact[norm])[:k]
        best: Dict[str, float] = {}
        for _name, score, idx in process.extract(
            norm, self._icd_names, scorer=fuzz.token_set_ratio, limit=30
        ):
            if score < threshold:
                continue
            code = self._icd_name_codes[idx]
            if score > best.get(code, 0):
                best[code] = score
        ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked[:k]]

    def match_rxnorm(self, text: str, k: int = 1, threshold: int = 60) -> List[str]:
        """Trả top-k RxCUI cho 1 span thuốc (rỗng nếu không đủ tin cậy).

        token_sort_ratio (không phải token_set): ưu tiên clinical drug khớp cả liều
        thay vì ingredient trần (span 'amlodipine 10 mg' -> SCD 308135, không phải IN).
        """
        norm = normalize_for_match(text)
        if not norm:
            return []
        if norm in self._rxn_exact:
            return list(self._rxn_exact[norm])[:k]
        head = _head_token(norm)
        cands = self._rxn_block.get(head, []) if head else []
        if not cands:
            return []
        best: Dict[str, float] = {}
        for cand_norm, rxcui in cands:
            score = fuzz.token_sort_ratio(norm, cand_norm)
            if score < threshold:
                continue
            if score > best.get(rxcui, 0):
                best[rxcui] = score
        ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked[:k]]
