# exp_0001_baseline — ghi chú

## Đã làm
- Dựng **nền tảng**: schema, eval harness (metric WER+Jaccard+weighted candidates, đã
  validate = 1.0 trên ví dụ đề), I/O + offset finder (giữ offset raw), KB loader/matcher.
- Pipeline **Tier 0** chạy end-to-end: 15 file dev + 100 file test → JSON hợp lệ +
  `output.zip`. 100 file/32s, 980 concept.

## Điểm số
- **PENDING_GOLD** — chưa chấm vì `data/labeled/ground_truth/` còn rỗng. Nhãn nháp (từ
  pipeline) ở `data/labeled/ground_truth_draft/` chờ người sửa; chấm thẳng lên draft =
  circular (~1.0 giả), nên `run_eval.py` chỉ đọc `ground_truth/`.

## Hạn chế đã quan sát (định hướng Tier 1)
- **Extraction**: bỏ hẳn section tường thuật (diễn biến/sự kiện/thủ thuật) để giữ
  precision → **sót** thuốc/triệu chứng nằm trong văn xuôi (vd prednisone/amoxicillin
  trong đoạn kể của 50.txt). Recall sẽ là điểm yếu chính.
- **Candidate thuốc**: fuzzy chọn nhầm granularity (ingredient vs SCD đúng liều) trong
  nhiều trường hợp — token_sort_ratio giảm bớt nhưng chưa chuẩn. Cần parse hoạt
  chất+hàm lượng+dạng bào chế (Tier 1).
- **Candidate ICD**: tên bệnh chung ("viêm phổi") map vào mã chuyên biệt thay vì mã 3 ký
  tự tổng quát; tên lay ("hen suyễn") không khớp tên ICD ("Hen") → cần alias/đồng nghĩa.
- **Assertion**: rule đơn giản; isNegated dựa cue trong dòng dễ nhầm (vd "Nôn không ra
  máu"); isFamily conservative (hiếm khi bắn).

## Chạy lại
```
python -m src.pipeline --input data/raw/input --output experiments/exp_0001_baseline/predictions_test
python scripts/make_submission.py --pred experiments/exp_0001_baseline/predictions_test --out experiments/exp_0001_baseline/output.zip
python scripts/run_eval.py --pred experiments/exp_0001_baseline/predictions   # sau khi có gold
```
