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

## Hiện trạng (gold v1)

- **15 file** đã gán nhãn dùng để chấm: `input/{i}.txt` + `ground_truth/{i}.json` với i ∈ {3, 6, 8, 31, 35, 36, 37, 50, 51, 66, 70, 82, 84, 87, 91}. (`input/` còn 54.txt, 97.txt thuộc bản nháp, chưa vào bộ chấm chính.)
- **Sinh bằng code, không sửa tay JSON**: annotation nằm trong [`../../scripts/gold_annotations.py`](../../scripts/gold_annotations.py) → chạy [`../../scripts/build_gold.py`](../../scripts/build_gold.py) sinh ra `ground_truth/` (tính offset bằng cursor tuần tự, validate `raw[start:end]==text`). Sửa nhãn → sửa `gold_annotations.py` rồi chạy lại `build_gold.py` (`--check` để chỉ validate).
- **`ground_truth_draft/`** = bản nháp trước verify; **`ground_truth/`** = bản dùng để chấm (`src/eval/`). Chọn mẫu: [`SELECTION.md`](SELECTION.md).
- ⚠️ **gold v1 INCOMPLETE** (assistant-annotated): đếm sót occurrence, candidate best-effort → `text_score`/`candidates_score` dev **không tin tuyệt đối**, chỉ dùng so sánh tương đối; điểm thật lấy từ submission BTC ([`../../docs/EXPERIMENTS_LOG.md`](../../docs/EXPERIMENTS_LOG.md)).
