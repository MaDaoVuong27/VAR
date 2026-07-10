# Viettel AI Race — Medical NER + Ontology Reasoning (tiếng Việt)

Bài toán: từ văn bản y khoa tự do tiếng Việt, phát hiện & phân loại khái niệm y tế, ánh xạ `CHẨN_ĐOÁN`/`THUỐC` sang ICD-10/RxNorm, và suy luận assertion ngữ cảnh (phủ định / người nhà / tiền sử). Chi tiết đầy đủ: [`TASK/de_bai.md`](TASK/de_bai.md), [`TASK/de_bai_chi_tiet.md`](TASK/de_bai_chi_tiet.md); bản tóm tắt tra cứu nhanh: [`docs/TASK_SPEC.md`](docs/TASK_SPEC.md).

> Teammate mới hoặc AI agent (Claude Code, Codex...) làm việc trong repo này: đọc [`CLAUDE.md`](CLAUDE.md) trước — vai trò từng thư mục, quy tắc bắt buộc, và cách tương tác với `docs/`.

## Bắt đầu từ đâu

Đọc theo thứ tự trong `docs/` để nắm toàn bộ bối cảnh mà không cần đọc code:

1. [`docs/TASK_SPEC.md`](docs/TASK_SPEC.md) — đề bài rút gọn + công thức chấm điểm.
2. [`docs/IDEAS.md`](docs/IDEAS.md) — ý tưởng đang theo đuổi, ý tưởng đã thử/loại bỏ.
3. [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md) — model/tham số đang dùng trong `src/`.
4. [`docs/EXPERIMENTS_LOG.md`](docs/EXPERIMENTS_LOG.md) — bảng so sánh kết quả mọi experiment.

## Cấu trúc repo

```
TASK/               # đề bài gốc + metric (không sửa)
docs/               # tài liệu tổng hợp — đọc trước khi đọc code
knowledge_base/     # ICD-10 + RxNorm dùng cho candidate mapping (đang TODO nguồn)
data/
  raw/              # input gốc từ BTC (100 file .txt của test vòng 1, không có nhãn)
  labeled/          # tập dev tự gán nhãn (input + ground_truth) để src/eval/ tự chấm điểm
  synthetic/        # dữ liệu tự sinh thêm để train
models/             # model weights/checkpoint dùng chung giữa các experiment (weight gitignored)
src/                # code chính: extraction / normalization / assertion / eval / pipeline
notebooks/          # EDA, error analysis nhanh — tách biệt code sản xuất
experiments/        # mỗi thử nghiệm 1 folder (config + predictions + metrics)
references/         # code/paper SOTA về RAG, reasoning, ontology để tham khảo
scripts/            # đóng gói submission, tải knowledge base, chạy eval hàng loạt
```

## Ràng buộc cần nhớ

- Nếu dùng LLM/agent: self-host, **tối đa 9B params**, **không gọi API ngoài**.
- Top ~15 đội phải nộp lại source code + data + model weights + README cài đặt để BTC chạy trên private test — tránh hard-code theo input đề cho.
