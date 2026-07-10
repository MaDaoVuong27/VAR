# Scripts

Tiện ích hỗ trợ, không phải logic chính của bài toán (logic chính nằm ở `src/`).

Dự kiến sẽ chứa:

- Script đóng gói `predictions/` của 1 experiment thành `output.zip` đúng format nộp bài (`output/{i}.json`).
- Script tải/dựng `knowledge_base/` (ICD-10, RxNorm) khi đã chốt nguồn.
- Script chạy eval hàng loạt (gọi `src/eval/`) trên nhiều experiment cùng lúc.

_(chưa có script nào — thêm khi `src/` đã có pipeline chạy được)_
