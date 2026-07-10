# data/labeled — tập dev tự gán nhãn

`data/raw/input/` là tập test của BTC — **không có ground truth**. Để `src/eval/` có cơ sở tính điểm (`text_score`/`assertions_score`/`candidates_score`) trước khi nộp bài, cần 1 tập dev tự gán nhãn, cấu trúc mirror format chính thức:

```
data/labeled/
├── input/           # {i}.txt — văn bản đầu vào (tự sưu tầm hoặc trích 1 phần từ data/synthetic/)
└── ground_truth/     # {i}.json — nhãn đúng, cùng format với output nộp bài (xem docs/TASK_SPEC.md)
```

Mỗi `input/{i}.txt` phải có đúng 1 `ground_truth/{i}.json` tương ứng.

## Quy trình dùng

1. Gán nhãn thủ công (hoặc bán tự động rồi review lại) cho 1 số mẫu — càng đa dạng loại văn bản (giấy xuất viện, đơn thuốc, kết quả xét nghiệm...) càng tốt.
2. Chạy pipeline trong `src/` trên `data/labeled/input/` → predictions.
3. `src/eval/` so sánh predictions với `data/labeled/ground_truth/` → ra `text_score`/`assertions_score`/`candidates_score`/`final_score`.
4. Dùng kết quả này để log vào `experiments/expXXXX/metrics.json` và `docs/EXPERIMENTS_LOG.md`.

_(chưa có sample nào được gán nhãn)_
