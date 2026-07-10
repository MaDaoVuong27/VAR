# Tổng hợp kết quả thử nghiệm

Bảng roll-up của mọi experiment trong `experiments/`. Mỗi dòng ứng với 1 folder `experiments/exp_XXXX_<tên>/`. Chi tiết cấu hình từng experiment nằm trong `config.yaml` của folder đó; chi tiết ý tưởng đứng sau nằm trong [IDEAS.md](IDEAS.md).

Công thức nhắc lại: `final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score`

| ID | Ngày | Mô tả ngắn | text_score | assertions_score | candidates_score | final_score | Nhận xét |
|---|---|---|---|---|---|---|---|
| _(chưa có experiment nào)_ | | | | | | | |

---

## Cách thêm 1 experiment mới vào bảng trên

1. Tạo folder `experiments/exp_XXXX_<tên-ngắn-gọn>/` (xem `experiments/README.md`).
2. Chạy pipeline, sinh `predictions/*.json`, chạy `src/eval/` để ra `metrics.json`.
3. Thêm 1 dòng vào bảng trên, link tới folder experiment.
4. Nếu experiment dẫn tới thay đổi hướng đi, cập nhật [IDEAS.md](IDEAS.md) (mục ý tưởng đã thử/loại bỏ).
