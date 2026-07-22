"""Kiểm thử metric bằng ví dụ trong TASK/de_bai_chi_tiet.md.

Chạy: python tests/test_metric.py  (không cần pytest)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema import Concept
from src.eval.metric import score_dataset


def _clone(c: Concept) -> Concept:
    return Concept(c.text, c.type, list(c.position), list(c.assertions), list(c.candidates))


GOLD = [
    Concept("amlodipine 10 mg po daily", "THUỐC", [58, 83], ["isHistorical"], ["308135"]),
    Concept("aspirin 81 mg po daily", "THUỐC", [89, 111], ["isHistorical"], ["243670"]),
    Concept("ho", "TRIỆU_CHỨNG", [196, 198], [], []),
    Concept("táo bón", "TRIỆU_CHỨNG", [397, 404], [], []),
    Concept("clonazepam 0.5 mg po qam:prn", "THUỐC", [457, 485], ["isHistorical"], ["197527"]),
]


def test_perfect():
    s = score_dataset({"1": [_clone(c) for c in GOLD]}, {"1": GOLD})
    assert s.final_score == 1.0, s.as_dict()


def test_wrong_candidate_drops_candidates():
    pred = [_clone(c) for c in GOLD]
    pred[0].candidates = ["999999"]
    s = score_dataset({"1": pred}, {"1": GOLD})
    assert s.candidates_score < 1.0 and s.text_score == 1.0 and s.assertions_score == 1.0


def test_missing_assertion_drops_assertions():
    pred = [_clone(c) for c in GOLD]
    pred[1].assertions = []
    s = score_dataset({"1": pred}, {"1": GOLD})
    assert s.assertions_score < 1.0 and s.candidates_score == 1.0


def test_wrong_type_penalizes():
    pred = [_clone(c) for c in GOLD]
    pred[2] = Concept("ho", "CHẨN_ĐOÁN", [196, 198], [], ["R05"])
    s = score_dataset({"1": pred}, {"1": GOLD})
    assert s.text_score < 1.0 and s.candidates_score < 1.0


def test_empty_pred():
    s = score_dataset({"1": []}, {"1": GOLD})
    assert s.text_score == 0.0 and s.candidates_score == 0.0


def test_abstain_beats_wrong_code_on_spurious():
    """Concept THỪA + abstain ăn J(∅,∅)=1; gán mã cho nó thì ăn 0. ĐÃ KIỂM CHỨNG BẰNG BTC.

    A/B sạch exp_0010(th=0.7, coverage 49%) vs exp_0012(th=0.5, coverage 99%) — chỉ khác
    matcher, BTC báo WER & J_assertion y hệt: cand 19.0448 -> 13.2899 (TỤT 30%). Tức phủ
    mã cho span rác LÀM TỤT ĐIỂM => abstain sinh điểm thật. Test này khoá hành vi đó lại.
    Xem §5 docstring metric.py — đừng đảo ngược nếu chưa có bằng chứng BTC mới.
    """
    junk_abstain = [_clone(c) for c in GOLD] + [Concept("bệnh nhân", "CHẨN_ĐOÁN", [0, 9], [], [])]
    junk_coded = [_clone(c) for c in GOLD] + [Concept("bệnh nhân", "CHẨN_ĐOÁN", [0, 9], [], ["R69"])]
    s_abstain = score_dataset({"1": junk_abstain}, {"1": GOLD})
    s_coded = score_dataset({"1": junk_coded}, {"1": GOLD})
    assert s_abstain.candidates_score > s_coded.candidates_score, (
        s_abstain.as_dict(), s_coded.as_dict())


def test_matched_concept_with_empty_gold_scores_one():
    """Concept CÓ THẬT đã ghép mà gold cũng không có mã -> J(∅,∅)=1 (quy ước đề)."""
    gold = [Concept("ho", "TRIỆU_CHỨNG", [196, 198], [], []),
            Concept("sốt", "CHẨN_ĐOÁN", [0, 3], [], [])]  # gold không có mã
    pred = [_clone(c) for c in gold]
    s = score_dataset({"1": pred}, {"1": gold})
    assert s.candidates_score == 1.0 and s.assertions_score == 1.0, s.as_dict()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed.")
