# Experiments

Mỗi thử nghiệm là 1 folder độc lập, tự chứa cấu hình + kết quả, để có thể so sánh giữa các lần chạy mà không ghi đè lẫn nhau.

## Quy ước đặt tên

```
experiments/exp_0001_<tên-ngắn-gọn>/
```

Đánh số tăng dần theo thứ tự tạo, không tái sử dụng số cũ.

## Cấu trúc bên trong 1 experiment

```
exp_0001_<tên>/
├── config.yaml        # toàn bộ tham số/model dùng cho lần chạy này
├── predictions/        # output .json theo từng bản ghi (1.json, 2.json, ...)
├── metrics.json         # text_score, assertions_score, candidates_score, final_score
└── notes.md             # (tuỳ chọn) quan sát/nhận xét riêng của lần chạy này
```

## Sau khi chạy xong 1 experiment

Thêm 1 dòng vào bảng tổng hợp ở [`../docs/EXPERIMENTS_LOG.md`](../docs/EXPERIMENTS_LOG.md) — đó là nơi tra cứu nhanh để so sánh, không cần mở từng folder.

## Danh sách hiện tại

Chi tiết + điểm (dev & thật BTC): [`../docs/EXPERIMENTS_LOG.md`](../docs/EXPERIMENTS_LOG.md).

| Folder | Mô tả ngắn |
|---|---|
| `exp_0001_baseline/` | Tier 0: rule/dict NER + assertion rule + fuzzy candidate (0 model). |
| `exp_0002_tier1_hybrid/` | dense MiniLM + lexical cho ICD candidate — ❌ loại (embedder general yếu). |
| `exp_0003_ner_xlmr/` | Tier 1: NER XLM-R v2 (min_conf 0.95) + rule assertion + fuzzy. **best thật BTC (22.18)**. |
| `exp_0003b_ner_conf06/` | A/B min_conf=0.6 — ❌ tệ hơn → chốt 0.95. |
| `exp_0004_ner_sapbert/` | NER + SapBERT candidate (k=1). |
| `exp_0005_ner_hybrid/` | NER + hybrid (fuzzy trước, SapBERT lấp). |
| `exp_0006_hybrid_th07/` | NER + hybrid, SapBERT abstain th=0.7. |
| `exp_0007_sapbert_th07/` | NER + SapBERT-only abstain th=0.7 (thay fuzzy) + tách span xuống dòng — **bản đề xuất nộp**. |

> ⚠️ Quy ước `config.yaml` chưa được tuân thủ đều: hiện chỉ `exp_0001` và `exp_0007` có `config.yaml`; các exp khác ghi cấu hình trong `metrics.json` (`exp`/`desc`/`ner`) + lệnh `scripts/run_pipeline_exp.py`. Experiment mới nên kèm `config.yaml`.
