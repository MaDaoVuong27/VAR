# Scripts

Tiện ích hỗ trợ (logic chính nằm ở `src/`). Chạy từ gốc repo.

## Chạy pipeline & chấm điểm

| Script | Việc |
|---|---|
| `run_pipeline_exp.py` | **Chạy 1 experiment đầy đủ**: pipeline trên dev + test → eval dev → đóng gói `output.zip` → ghi `metrics.json`. Cờ chọn NER/candidate (xem ví dụ dưới). |
| `run_eval.py` | Chấm `predictions/` vs `ground_truth/` (dùng `src/eval/metric.py`). |
| `make_submission.py` | Đóng gói 1 thư mục `{i}.json` → `output.zip` đúng format `output/{i}.json`. |

## Train / build dữ liệu

| Script | Việc |
|---|---|
| `train_ner.py` | Fine-tune NER XLM-R token-classification trên `data/synthetic/` → `models/ner_xlmr*`. |
| `build_gold.py` | Sinh `data/labeled/ground_truth/*.json` từ `gold_annotations.py` (offset cursor tuần tự + validate `raw[s:e]==text`). `--check` chỉ validate, không ghi. |
| `gold_annotations.py` | **Dữ liệu** annotation gold v1 cho 15 file dev (không phải script chạy — bảng nhãn Python, `build_gold.py` import). |
| `build_icd10_vn.py` | Parse `icd10/raw/06-byt-kem.pdf` (29 cột) → `icd10/processed/icd10_vn.csv`. |
| `build_rxnorm_processed.py` | Lọc `rxnorm/raw/rrf/RXNCONSO.RRF` (SAB=RXNORM, mọi TTY) → `rxnorm/processed/rxnorm_terms.csv`. |

> `processed/*.csv` đã track trong git → **không cần chạy lại `build_icd10_vn`/`build_rxnorm_processed`** trừ khi build lại KB từ raw (cần tải raw, xem `knowledge_base/*/raw/SOURCE.md`).

## Ví dụ: tái tạo bản đề xuất nộp (exp_0007)

```bash
python scripts/run_pipeline_exp.py --exp exp_0007_sapbert_th07 \
    --ner models/ner_xlmr_v2 --min-conf 0.95 --sapbert --sap-th 0.7 \
    --desc "NER + SapBERT abstain th=0.7 + tach span xuong dong"
```

Cần: `models/ner_xlmr_v2/model.safetensors` (copy tay / train lại) + cache SapBERT (tự build lần đầu). Xuất `experiments/exp_0007_sapbert_th07/{predictions_test/, output.zip, metrics.json}`.

Các cờ khác của `run_pipeline_exp.py`: bỏ `--ner` = dùng rule extractor (baseline); `--hybrid` = fuzzy trước, SapBERT lấp khi rỗng; bỏ cả `--sapbert`/`--hybrid` = fuzzy KB thuần.
