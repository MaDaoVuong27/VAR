# -*- coding: utf-8 -*-
"""Cổng chất lượng cho synthetic data — chạy TRƯỚC khi dùng để train (bắt buộc theo
docs/SYNTHETIC_V5_PLAN.md §4.2 "Cổng chất lượng").

Kiểm tra:
  1. Offset invariant: raw[s:e] == text cho MỌI concept (cứng, phải 0 lỗi).
  2. LCS ratio vs 100 file test: cảnh báo/loại nếu >= ngưỡng (mặc định 0.5) — chống paraphrase
     quá gần tập test (xem IDEA 7 §Ranh giới).
  3. n-gram-13 trùng test: đếm số n-gram dài trùng nguyên văn — phải gần 0.
  4. Phân bố type/độ dài/entity-density — so với test thật để canh tỉ lệ.
  5. Phân bố assertion — so với dev gold (xem SYNTHETIC_V5_PLAN.md §2).

Usage:
    python scripts/audit_synthetic.py --data data/synthetic/frame_v5.jsonl
    python scripts/audit_synthetic.py --data data/synthetic/train_v5a.jsonl --lcs-threshold 0.5
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent

CANDIDATE_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}
ASSERTION_TYPES = {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}


def _load_jsonl(path: Path) -> List[dict]:
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_test_docs(input_dir: str) -> List[str]:
    p = ROOT / input_dir
    if not p.exists():
        p = ROOT / "data" / "raw" / "input"
    return [open(f, encoding="utf-8").read() for f in sorted(p.glob("*.txt"))]


def check_offset_invariant(rows: List[dict]) -> int:
    bad = 0
    for r in rows:
        for c in r["concepts"]:
            s, e = c["position"]
            if r["text"][s:e] != c["text"]:
                bad += 1
    return bad


def _lcs_len(a: List[str], b: List[str]) -> int:
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            cur[j] = prev[j - 1] + 1 if ai == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[m]


def _longest_contiguous_run(a: List[str], b: List[str]) -> int:
    """Chuỗi từ khớp LIÊN TỤC dài nhất — phân biệt leakage thật (copy nguyên đoạn) với LCS
    (subsequence, có thể khớp rời rạc qua từ nối chung như 'không'/'có'/'ghi nhận')."""
    import difflib
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blk = sm.find_longest_match(0, len(a), 0, len(b))
    return blk.size


def check_lcs_vs_test(rows: List[dict], test_docs: List[str], threshold: float,
                       sample: int, max_words: int, min_contiguous: int = 6):
    """LCS (subsequence) một mình DỄ BÁO ĐỘNG GIẢ: 2 câu tiếng Việt y khoa dùng chung từ nối phổ
    thông ("không", "có", "ghi nhận", "tiền sử"...) có thể ra LCS ratio cao dù không hề copy đoạn
    nào. Đã đo: LCS=0.643 nhưng chuỗi khớp LIÊN TỤC dài nhất chỉ 2 từ ("khó thở") — không phải
    leakage. Chỉ coi là leakage thật khi CẢ HAI: LCS ratio >= threshold VÀ có chuỗi liên tục
    >= min_contiguous từ (dấu hiệu chép nguyên cụm, không phải trùng từ vựng chung).
    """
    import random
    rng = random.Random(0)
    test_words = [d.lower().split()[:max_words * 3] for d in test_docs]
    samp = rng.sample(rows, min(sample, len(rows)))
    flagged, noise = [], []
    for r in samp:
        a = r["text"].lower().split()[:max_words]
        best_lcs, best_run, best_doc = 0.0, 0, None
        for b in test_words:
            lcs = _lcs_len(a, b) / max(1, len(a))
            if lcs > best_lcs:
                best_lcs, best_doc = lcs, b
        if best_lcs >= threshold and best_doc is not None:
            run = _longest_contiguous_run(a, best_doc)
            entry = (best_lcs, run, r["text"][:80])
            (flagged if run >= min_contiguous else noise).append(entry)
    flagged.sort(reverse=True)
    noise.sort(reverse=True)
    return flagged, noise, len(samp)


def check_ngram_overlap(rows: List[dict], test_docs: List[str], n: int = 13):
    test_ng = set()
    for d in test_docs:
        w = d.lower().split()
        for i in range(len(w) - n + 1):
            test_ng.add(tuple(w[i:i + n]))
    hits = total = 0
    for r in rows:
        w = r["text"].lower().split()
        for i in range(len(w) - n + 1):
            total += 1
            if tuple(w[i:i + n]) in test_ng:
                hits += 1
    return hits, total


def check_distribution(rows: List[dict]):
    lens = sorted(len(r["text"]) for r in rows)
    type_c = Counter(c["type"] for r in rows for c in r["concepts"])
    n = len(rows)
    ent_per_doc = sum(type_c.values()) / max(n, 1)
    return {
        "n_docs": n,
        "len_min": lens[0] if lens else 0,
        "len_median": lens[len(lens) // 2] if lens else 0,
        "len_max": lens[-1] if lens else 0,
        "type_dist": dict(type_c),
        "entities_per_doc": round(ent_per_doc, 2),
    }


def check_assertion_distribution(rows: List[dict]):
    c = Counter()
    for r in rows:
        for concept in r["concepts"]:
            if concept["type"] not in ASSERTION_TYPES:
                continue
            key = tuple(sorted(concept.get("assertions") or []))
            c[key if key else ("(rỗng)",)] += 1
    tot = sum(c.values())
    return {("+".join(k)): round(v / max(tot, 1), 4) for k, v in c.most_common()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="1 file .jsonl hoặc pattern glob")
    ap.add_argument("--test-input", default="data/raw_new/input")
    ap.add_argument("--lcs-threshold", type=float, default=0.5)
    ap.add_argument("--lcs-sample", type=int, default=200, help="số doc lấy mẫu để tính LCS")
    ap.add_argument("--lcs-max-words", type=int, default=220)
    args = ap.parse_args()

    paths = [Path(p) for p in glob.glob(args.data)] or [ROOT / args.data]
    rows: List[dict] = []
    for p in paths:
        rows += _load_jsonl(p if p.is_absolute() else ROOT / p)
    if not rows:
        raise SystemExit(f"[audit] Không đọc được doc nào từ {args.data}")

    print(f"=== Audit synthetic: {args.data} ({len(rows)} doc) ===\n")

    bad = check_offset_invariant(rows)
    print(f"[1] Offset invariant: {bad} lỗi / {sum(len(r['concepts']) for r in rows)} entity "
          f"{'✅' if bad == 0 else '❌ PHẢI SỬA TRƯỚC KHI DÙNG'}")

    test_docs = _load_test_docs(args.test_input)
    flagged, noise, n_sampled = check_lcs_vs_test(
        rows, test_docs, args.lcs_threshold, args.lcs_sample, args.lcs_max_words)
    print(f"\n[2] LCS vs test (mẫu {n_sampled} doc, ngưỡng {args.lcs_threshold}, "
          f"cần chuỗi liên tục >={6} từ mới tính leakage thật): "
          f"{len(flagged)} doc {'✅' if not flagged else '⚠️  CẦN REVIEW/LOẠI'}"
          f" ({len(noise)} doc LCS cao nhưng KHÔNG có chuỗi liên tục dài -> nhiễu do từ vựng"
          f" y khoa chung, không phải leakage)")
    for lcs, run, snippet in flagged[:5]:
        print(f"     LCS={lcs:.3f} chuỗi_liên_tục={run}từ  {snippet!r}")
    if noise and not flagged:
        print(f"     (ví dụ noise đã loại: LCS={noise[0][0]:.3f} nhưng chuỗi liên tục chỉ "
              f"{noise[0][1]} từ — {noise[0][2]!r})")

    hits, total = check_ngram_overlap(rows, test_docs)
    pct = 100 * hits / max(total, 1)
    print(f"\n[3] n-gram-13 trùng test: {hits}/{total} ({pct:.4f}%) "
          f"{'✅' if pct < 0.1 else '⚠️  CAO BẤT THƯỜNG'}")

    dist = check_distribution(rows)
    print(f"\n[4] Phân bố: {dist}")

    adist = check_assertion_distribution(rows)
    print(f"\n[5] Phân bố assertion: {adist}")
    print("    (đối chiếu dev gold: isHistorical~43%, rỗng~41%, isNegated~14%, isFamily~3%, combo~0%)")


if __name__ == "__main__":
    main()
