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

_(chưa có experiment nào)_
