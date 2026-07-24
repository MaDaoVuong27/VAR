"""Metric tự chấm điểm (proxy nội bộ của công thức BTC — xem docs/TASK_SPEC.md).

final_score = 0.3*text_score + 0.3*assertions_score + 0.4*candidates_score

⚠️ GIẢ ĐỊNH DIỄN GIẢI (công thức đề còn vài chỗ chưa nói rõ — user đồng ý cho tự
implement + document, coi đây là proxy, có thể lệch nhẹ so với scorer BTC):

1. Ghép concept dự đoán ↔ ground truth theo từng sample: chỉ ghép khi **cùng type**
   và (text chuẩn hoá trùng khớp HOẶC position chồng lấn IoU > 0.5). Ghép greedy 1-1.
   → Đúng type là bắt buộc: đoán đúng text nhưng sai type = KHÔNG ghép → tính vừa
   thiếu (gold) vừa thừa (pred), 0 điểm cả 3 metric (khớp lưu ý trong đề).

2. text_score(i) = 1 - WER, WER = (word-edit trên các cặp đã ghép + toàn bộ word của
   gold chưa ghép [deletion] + toàn bộ word của pred chưa ghép [insertion]) / (tổng
   word của gold). Trung bình trên các sample.

3. assertions_score(i) = trung bình Jaccard(assertions) trên các concept type có
   assertion (CHẨN_ĐOÁN/THUỐC/TRIỆU_CHỨNG): mỗi gold concept lấy Jaccard với pred đã
   ghép (pred rỗng nếu chưa ghép); mỗi pred thừa tính như gold rỗng. Trung bình trên
   sample. J theo quy ước đề: cả 2 rỗng→1; gold rỗng & pred khác rỗng→0.

4. candidates_score = TRUNG BÌNH CÓ TRỌNG SỐ TOÀN CỤC (không theo sample) của
   Jaccard(candidates) trên concept type CHẨN_ĐOÁN/THUỐC, trọng số mỗi concept =
   len(gold_candidates)+1. = Σ_i Σ_k J_k·w_k / Σ_i Σ_k w_k. Pred thừa: gold rỗng, w=1.
   (Tương đương công thức J_candidates(i)·Σ_k w_k / Σ w trong đề khi J(i) là weighted-avg.)

5. ⚠️⚠️ CONCEPT THỪA + ABSTAIN ĂN J(∅,∅)=1 — ĐÃ KIỂM CHỨNG BẰNG BTC. ĐỪNG "SỬA" LẠI.
   2026-07-15 tôi từng đổi thành "concept thừa = 0 điểm", lập luận từ lưu ý đề ("concept
   sai type bị tính 2 lần, mỗi lần 0 điểm cả 3 metric"). **Bản sửa đó SAI.** Bằng chứng
   là một A/B sạch tuyệt đối — exp_0010 vs exp_0012 CHỈ khác matcher candidate (BTC xác
   nhận: WER 65.9308 và J_assertion 35.9491 giống hệt nhau ở cả hai):

       sap_th 0.7 (coverage 49%)  ->  sap_th 0.5 (coverage 99%)
       BTC thật     : 19.0448 -> 13.2899   TỤT 30%
       metric NÀY   :  0.4902 ->  0.1725   TỤT 65%   ✅ đúng hướng
       bản "đã sửa" :  0.1647 ->  0.1647   BẰNG NHAU  ❌ mù hoàn toàn

   → BTC áp dụng ĐÚNG CHỮ NGHĨA quy ước Jaccard, kể cả cho concept không khớp gold. Lưu ý
   "0 điểm cả 3 metric" trong đề chỉ nói ca SAI TYPE (text khớp gold nhưng type khác),
   KHÔNG áp cho mọi false-positive. → **Abstain THẬT SỰ sinh điểm khi NER over-predict.**

6. ⚠️ BÀI HỌC PHƯƠNG PHÁP: metric này lệch xa BTC về GIÁ TRỊ TUYỆT ĐỐI (0.49 vs 19.04) —
   bình thường, không sao. Thứ cần là XẾP HẠNG đúng. Bản "sửa" khớp tuyệt đối đẹp hơn
   (0.116 vs BTC 0.107) nhưng mất khả năng phân biệt → vô dụng. Độ khớp tuyệt đối là BẪY:
   nó chỉ trùng hợp vì gold dev thiếu nhãn triệt tiêu ngược lỗi vừa tạo ra.
   → KHÔNG BAO GIỜ tinh chỉnh metric này theo độ khớp tuyệt đối với BTC.

7. 🚨 **`_match()` MÔ PHỎNG SAI ĐỘ NHẠY của scorer BTC thật với lỗi `position` NẶNG** (phát hiện
   2026-07-24, exp_0031): test A/B cực đoan — lấy predictions đã ăn BTC thật 22.7685 (exp_0026),
   ghi đè TOÀN BỘ `position` thành `[0,0]`, giữ nguyên text/type/candidates/assertions, rồi nộp
   thật. Proxy này (OR: text-match hoặc position-IoU>0.5) dự đoán final chỉ giảm **−3.3%** (còn
   nhiều pair vẫn ghép được qua text). BTC thật giảm **−66%** (WER 72.17→100, J_assertion
   30.33→0). → scorer BTC thật có vẻ **dựa vào position CHẶT hơn nhiều** để ghép cặp — gần như
   bắt buộc, không phải fallback nhẹ như ở đây. Quy luật "cùng span → dev xếp hạng đáng tin" VẪN
   ĐÚNG cho so sánh giữa các model bình thường (đã kiểm chứng nhiều lần, position luôn hợp lý ở
   mọi trường hợp đó) — phát hiện này CHỈ áp dụng cho trường hợp cực đoan (position sai lệch
   hoàn toàn/vô nghĩa), không phải phản chứng cho quy luật đó. Nhưng nó ngụ ý: cải tiến độ chính
   xác BOUNDARY (position) có giá trị thật cao hơn con số dev proxy từng thể hiện — xem
   `experiments/exp_0031_position_ablation/notes.md` + `docs/EXPERIMENTS_LOG.md` §exp_0031.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..schema import ASSERTION_TYPES, CANDIDATE_TYPES, Concept

_WS = re.compile(r"\s+")


def _norm_text(s: str) -> str:
    return _WS.sub(" ", s.strip().lower())


def _words(s: str) -> List[str]:
    return _norm_text(s).split()


def _word_levenshtein(a: Sequence[str], b: Sequence[str]) -> int:
    """Số phép chèn/xoá/thay tối thiểu giữa 2 chuỗi word (DP O(n*m))."""
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[m]


def _iou(p1: Sequence[int], p2: Sequence[int]) -> float:
    if not p1 or not p2 or len(p1) < 2 or len(p2) < 2:
        return 0.0
    a0, a1 = p1[0], p1[1]
    b0, b1 = p2[0], p2[1]
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return inter / union if union > 0 else 0.0


def _jaccard(pred: Sequence[str], gold: Sequence[str]) -> float:
    """Jaccard theo quy ước đề (empty rules)."""
    ps, gs = set(pred), set(gold)
    if not gs and not ps:
        return 1.0
    if not gs and ps:
        return 0.0
    if gs and not ps:
        return 0.0
    return len(ps & gs) / len(ps | gs)


def _match(pred: List[Concept], gold: List[Concept]) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Ghép greedy 1-1 pred↔gold cùng type. Trả (pairs[(pi,gi)], pred_thừa_idx, gold_thiếu_idx)."""
    used_p, used_g = set(), set()
    scored: List[Tuple[float, int, int]] = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(pred):
            if p.type != g.type:
                continue
            if _norm_text(p.text) == _norm_text(g.text):
                s = 2.0  # ưu tiên khớp text tuyệt đối
            else:
                iou = _iou(p.position, g.position)
                s = iou if iou > 0.5 else 0.0
            if s > 0:
                scored.append((s, pi, gi))
    scored.sort(reverse=True)
    pairs = []
    for s, pi, gi in scored:
        if pi in used_p or gi in used_g:
            continue
        used_p.add(pi)
        used_g.add(gi)
        pairs.append((pi, gi))
    pred_extra = [i for i in range(len(pred)) if i not in used_p]
    gold_missed = [i for i in range(len(gold)) if i not in used_g]
    return pairs, pred_extra, gold_missed


@dataclass
class Scores:
    text_score: float
    assertions_score: float
    candidates_score: float
    final_score: float

    def as_dict(self) -> dict:
        return {
            "text_score": round(self.text_score, 4),
            "assertions_score": round(self.assertions_score, 4),
            "candidates_score": round(self.candidates_score, 4),
            "final_score": round(self.final_score, 4),
        }


def _sample_text_score(pred, gold, pairs) -> float:
    """text_score sample = soft-F1 trên text đã ghép (bounded [0,1], ổn định hơn WER thô).

    ⚠️ Khác công thức literal "1-WER" của đề: WER-with-insertions bị floor về 0 ngay khi
    pred có nhiều concept thừa/khác biên giới (dù có cặp khớp đúng) → vô dụng để so sánh.
    Thay bằng: mỗi cặp (type khớp) cho điểm (1 - word_WER(pred,gold)) trong [0,1]; chia
    cho max(#gold, #pred) để phạt cả bỏ sót (recall) lẫn thừa (precision). Perfect = 1.0.
    Khi có scorer chính thức BTC sẽ thay lại.
    """
    if not gold and not pred:
        return 1.0
    denom = max(len(gold), len(pred))
    if denom == 0:
        return 1.0
    credit = 0.0
    for pi, gi in pairs:
        gw, pw = _words(gold[gi].text), _words(pred[pi].text)
        wer = _word_levenshtein(pw, gw) / max(1, len(gw))
        credit += max(0.0, 1.0 - wer)
    return credit / denom


def score_sample(pred: List[Concept], gold: List[Concept]):
    """Trả (text_score, J_assertions, cand_num, cand_den) cho 1 sample.

    text/assertions là điểm sample; candidates trả (num,den) để cộng dồn toàn cục.
    """
    pairs, pred_extra, gold_missed = _match(pred, gold)

    # --- text ---
    text_score = _sample_text_score(pred, gold, pairs)

    # --- assertions (type có assertion) ---
    avals: List[float] = []
    pair_g = {gi: pi for pi, gi in pairs}
    for gi, g in enumerate(gold):
        if g.type not in ASSERTION_TYPES:
            continue
        pi = pair_g.get(gi)
        pa = pred[pi].assertions if pi is not None else []
        avals.append(_jaccard(pa, g.assertions))
    for pi in pred_extra:
        if pred[pi].type in ASSERTION_TYPES:
            avals.append(_jaccard(pred[pi].assertions, []))
    j_assert = sum(avals) / len(avals) if avals else 1.0

    # --- candidates (type có candidate) — trả num/den để cộng toàn cục ---
    cnum, cden = 0.0, 0.0
    for gi, g in enumerate(gold):
        if g.type not in CANDIDATE_TYPES:
            continue
        pi = pair_g.get(gi)
        pc = pred[pi].candidates if pi is not None else []
        w = len(g.candidates) + 1
        cnum += _jaccard(pc, g.candidates) * w
        cden += w
    for pi in pred_extra:
        if pred[pi].type in CANDIDATE_TYPES:
            w = 1  # gold rỗng -> len+1 = 1
            cnum += _jaccard(pred[pi].candidates, []) * w
            cden += w

    return text_score, j_assert, cnum, cden


def score_dataset(
    preds: Dict[str, List[Concept]],
    golds: Dict[str, List[Concept]],
) -> Scores:
    """Chấm trên tập file. Key = tên file; chỉ tính trên các file có trong golds."""
    keys = list(golds.keys())
    if not keys:
        return Scores(0.0, 0.0, 0.0, 0.0)
    t_sum, a_sum = 0.0, 0.0
    cnum_all, cden_all = 0.0, 0.0
    for k in keys:
        p = preds.get(k, [])
        g = golds[k]
        ts, ja, cn, cd = score_sample(p, g)
        t_sum += ts
        a_sum += ja
        cnum_all += cn
        cden_all += cd
    n = len(keys)
    text_score = t_sum / n
    assertions_score = a_sum / n
    candidates_score = (cnum_all / cden_all) if cden_all > 0 else 1.0
    final = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score
    return Scores(text_score, assertions_score, candidates_score, final)
