# ground_truth — nhãn dev

Thư mục này chứa nhãn dev mà `src/eval` + `scripts/run_eval.py` dùng để chấm điểm.

⚠️ **Hiện là gold v1 do ASSISTANT annotate** (đọc trực tiếp từng file, độc lập với baseline —
sinh bằng `scripts/build_gold.py` từ `scripts/gold_annotations.py`). **Cần người verify.**
- 13/15 file (thiếu `54`, `97` — dài, chưa annotate ở v1).
- Spans/types/assertions: khá tin cậy. **Candidate codes: best-effort** (ICD từ kiến thức lâm
  sàng; RxNorm ở mức hoạt chất — có thể khác SCD official). Đây là nguồn chính khiến
  candidates_score chưa chắc chắn tuyệt đối.
- Sửa nhãn: edit `scripts/gold_annotations.py` rồi chạy `python scripts/build_gold.py`.
