# src — code chính

Code chạy được của bài toán (khác với `references/` là code tham khảo, và `experiments/` là kết quả từng lần chạy).

## Module dự kiến

- `extraction/` — phát hiện khái niệm y tế trong text + phân loại `type` (5 nhãn).
- `normalization/` — ánh xạ `CHẨN_ĐOÁN` → ICD-10, `THUỐC` → RxNorm, dùng dữ liệu trong `knowledge_base/`.
- `assertion/` — xác định `isNegated` / `isFamily` / `isHistorical` cho `CHẨN_ĐOÁN`/`THUỐC`/`TRIỆU_CHỨNG`.
- `eval/` — implement đúng công thức chấm điểm trong `docs/TASK_SPEC.md` để tự đánh giá offline trước khi nộp.
- `pipeline.py` (sẽ thêm) — ghép các module trên thành 1 luồng: input `.txt` → output `.json` đúng format nộp bài.

Mọi model/tham số dùng trong các module này cần được cập nhật vào [`../docs/CONFIG_REFERENCE.md`](../docs/CONFIG_REFERENCE.md).

_(hiện tại mới chỉ là khung thư mục, chưa có code)_
