# -*- coding: utf-8 -*-
"""Catalog entity để sinh synthetic: bệnh (ICD), thuốc (RxNorm), triệu chứng, xét nghiệm.

Mỗi entity kèm candidate code (bệnh→ICD, thuốc→RxCUI) để nhãn synthetic có luôn candidate.
"""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import lexicons as LEX

_ROOT = Path(__file__).resolve().parent.parent.parent
_ICD = _ROOT / "knowledge_base" / "icd10" / "processed" / "icd10_vn.csv"
_RXN = _ROOT / "knowledge_base" / "rxnorm" / "processed" / "rxnorm_terms.csv"


@dataclass
class Entity:
    text: str
    type: str
    candidates: List[str] = field(default_factory=list)


class Catalog:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.diseases: List[Entity] = []       # CHẨN_ĐOÁN (vi/en name + ICD code)
        self.drugs: List[Entity] = []          # THUỐC (name + rxcui)
        self.symptoms: List[str] = []
        self.tests: List[str] = []

    def load(self, max_drugs: int = 20000) -> "Catalog":
        self._load_icd()
        self._load_rxn(max_drugs)
        self._load_lexicons()
        return self

    def _load_icd(self):
        with open(_ICD, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                code = (row.get("ma_benh") or "").strip()
                vi = (row.get("ten_benh_vi") or "").strip()
                en = (row.get("disease_name_en") or "").strip()
                if not code:
                    continue
                # bỏ tên quá dài (>10 từ) — ít giống cách viết trong note
                if vi and len(vi.split()) <= 10:
                    self.diseases.append(Entity(vi, "CHẨN_ĐOÁN", [code]))
                if en and len(en.split()) <= 8:
                    self.diseases.append(Entity(en, "CHẨN_ĐOÁN", [code]))

    def _load_rxn(self, max_drugs: int):
        # ưu tiên ingredient (IN/PIN) + brand (BN) — tên gọn, giống cách nhắc thuốc
        pool = []
        with open(_RXN, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                tty = row.get("tty", "")
                s = (row.get("str") or "").strip()
                rxcui = (row.get("rxcui") or "").strip()
                if not s or not rxcui:
                    continue
                if tty in ("IN", "PIN", "BN") and 1 <= len(s.split()) <= 5:
                    pool.append(Entity(s, "THUỐC", [rxcui]))
        self.rng.shuffle(pool)
        self.drugs = pool[:max_drugs]

    def _load_lexicons(self):
        self.symptoms = list(LEX.SYMPTOMS_VI) + list(LEX.SYMPTOMS_EN)
        self.tests = list(LEX.TEST_NAMES)
        # bổ sung triệu chứng từ chương R của ICD (tên VN ngắn)
        for e in self.diseases:
            pass  # diseases đã tách; R-chapter symptom sẽ lẫn trong diseases, giữ đơn giản

    # ---- sampler ----
    def disease(self) -> Entity:
        return self.rng.choice(self.diseases)

    def drug(self) -> Entity:
        return self.rng.choice(self.drugs)

    def symptom(self) -> str:
        return self.rng.choice(self.symptoms)

    def test(self) -> str:
        return self.rng.choice(self.tests)
