"""Pipeline baseline (Tier 0): input .txt -> output .json đúng format nộp bài.

Luồng 1 file: đọc raw -> extract (NER heuristic) -> gán assertion (rule) -> gán
candidates (KB fuzzy ICD/RxNorm) -> Concept -> JSON.

CLI:
    python -m src.pipeline --input data/raw/input --output <out_dir>
    python -m src.pipeline --input data/labeled/input --output <out_dir>
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .assertion import assign_assertions
from .common import read_input, write_output
from .extraction import extract_concepts
from .normalization import KnowledgeBase
from .schema import TYPE_CHAN_DOAN, TYPE_THUOC, Concept


def predict_file(raw: str, kb: KnowledgeBase, icd_k: int = 3, rxn_k: int = 1) -> List[Concept]:
    mentions = extract_concepts(raw, kb)
    assign_assertions(raw, mentions)

    # dedup theo (type, start, end)
    seen = set()
    concepts: List[Concept] = []
    for m in mentions:
        key = (m.type, m.start, m.end)
        if key in seen:
            continue
        seen.add(key)
        candidates: List[str] = []
        if m.type == TYPE_CHAN_DOAN:
            candidates = kb.match_icd(m.text, k=icd_k)
        elif m.type == TYPE_THUOC:
            candidates = kb.match_rxnorm(m.text, k=rxn_k)
        concepts.append(
            Concept(
                text=m.text,
                type=m.type,
                position=[m.start, m.end],
                assertions=list(getattr(m, "assertions", []) or []),
                candidates=candidates,
            )
        )
    return concepts


def run_dir(input_dir, output_dir, kb: KnowledgeBase = None) -> None:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if kb is None:
        kb = KnowledgeBase().load()
    files = sorted(input_dir.glob("*.txt"), key=lambda p: (len(p.stem), p.stem))
    for p in files:
        raw = read_input(p)
        concepts = predict_file(raw, kb)
        write_output(concepts, output_dir / f"{p.stem}.json")
    print(f"Wrote {len(files)} predictions to {output_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    run_dir(args.input, args.output)


if __name__ == "__main__":
    main()
