# References — SOTA papers & code

Nơi pull code/paper tham khảo (RAG, reasoning, ontology mapping...) để đọc và đánh giá khả năng áp dụng vào bài toán. Đây là thư viện tham khảo, **không phải code chạy được của dự án** (code chính nằm ở `src/`).

## Cấu trúc

Mỗi paper/repo là 1 folder con riêng, phẳng ngay dưới `references/` (không chia theo category):

```
references/
├── <ten-paper-1>/
│   ├── NOTES.md
│   └── code/
├── <ten-paper-2>/
│   ├── NOTES.md
│   └── code/
└── ...
```

## Quy ước khi thêm 1 tham khảo mới

Copy [`_TEMPLATE/`](_TEMPLATE/) (đổi tên, bỏ dấu `_`), điền `NOTES.md` gồm:

- Link gốc (paper/arxiv, GitHub repo)
- Ý tưởng chính (2-3 câu)
- Có thể áp dụng gì cho bài toán này (liên hệ tới `docs/IDEAS.md`)
- Giới hạn/không phù hợp ở điểm nào (vd: cần model > 9B, cần API ngoài, chỉ hỗ trợ tiếng Anh...)

Đặt code đã pull về trong `code/` — nếu repo gốc nặng (checkpoint, dataset lớn), chỉ giữ phần code cần đọc, không commit weights/data.

## Danh sách hiện tại

_(chưa có tham khảo nào được thêm, ngoài `_TEMPLATE`)_
