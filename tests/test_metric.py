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


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed.")
