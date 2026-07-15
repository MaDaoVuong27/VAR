# notebooks — EDA & error analysis

Notebook thăm dò dữ liệu, soi lỗi từng sample, thử nghiệm nhanh ý tưởng trước khi đưa vào `src/`. Tách biệt khỏi `src/` để code sản xuất luôn sạch — notebook ở đây được phép lộn xộn, không cần refactor.

Gợi ý đặt tên: `YYYYMMDD_mô-tả-ngắn.ipynb` (vd: `20260710_eda_input_samples.ipynb`) để dễ tra theo thời gian.

Nếu 1 kỹ thuật trong notebook chứng minh hiệu quả và được đưa vào pipeline chính thức, ghi lại trong `docs/IDEAS.md`.

## Hiện có

- `eda_features.py` — script tag feature 100 file test (độ dài, section, code-switch, cue phủ định, token dính liền...). Chạy: `python notebooks/eda_features.py`.
- `eda_outputs/feature_matrix.csv` — cờ + số đo từng file; `eda_outputs/eda_report.md` — phân bố + bảng chọn 15 file dev.

Kết quả EDA đã tổng hợp vào [`../docs/EDA_FINDINGS.md`](../docs/EDA_FINDINGS.md).
