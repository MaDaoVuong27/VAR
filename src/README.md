# src — code chính

Code chạy được của bài toán (khác `references/` = code tham khảo, `experiments/` = kết quả từng lần chạy).

## Module

| Path | Vai trò |
|---|---|
| `pipeline.py` | Ghép các khối: input `.txt` → concepts → output `.json`. `run_dir()` chạy cả thư mục; `predict_file()` cho 1 file. |
| `schema.py` | Định nghĩa `Concept` + hằng số 5 type. |
| `common/` | `io_utils.py` (đọc/ghi JSON, gold), `text_norm.py` (normalize cho matching — **giữ nguyên offset raw**). |
| `extraction/` | `extractor.py` (rule/heuristic — baseline Tier 0); `ner_extractor.py` + `ner_common.py` (NER XLM-R — Tier 1, **đang dùng**). |
| `normalization/` | `kb.py` (fuzzy ICD/RxNorm — baseline); `sapbert.py` (entity linking SapBERT — Tier 1, bản nộp); `dense.py` (dense off-the-shelf — exp_0002, đã loại). |
| `assertion/` | `rules.py` — gán `isNegated`/`isFamily`/`isHistorical` bằng rule (section + cue). |
| `eval/` | `metric.py` — công thức chấm (`text`/`assertions`/`candidates`/`final`) để tự đánh giá offline. |
| `synthetic/` | Sinh training data: `catalog.py` (danh mục entity từ KB), `lexicons.py` (lexicon triệu chứng/xét nghiệm/kết quả), `generate.py` (template + slot-fill → `data/synthetic/*.jsonl`). |

## Chạy

- Baseline trực tiếp: `python -m src.pipeline --input data/raw/input --output <out_dir>`.
- Đầy đủ (NER + SapBERT) + eval + đóng gói: `scripts/run_pipeline_exp.py` (xem [`../scripts/README.md`](../scripts/README.md)).

Mọi model/tham số dùng trong các module này phải được cập nhật vào [`../docs/CONFIG_REFERENCE.md`](../docs/CONFIG_REFERENCE.md).
