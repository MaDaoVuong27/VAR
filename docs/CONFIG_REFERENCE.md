# Tổng hợp tham số / model / settings

Nguồn sự thật cho toàn bộ tham số, model, và cấu hình đang được dùng trong `src/`. Cập nhật file này **mỗi khi** thêm/đổi model hoặc tham số quan trọng trong code — mục tiêu là đọc file này là biết code đang chạy gì, không cần lục code.

Lưu ý ràng buộc đề bài: nếu dùng LLM/agent, bắt buộc **self-host, tối đa 9B params, không gọi API ngoài** (xem [TASK_SPEC.md](TASK_SPEC.md)). Cột "Params" bên dưới dùng để tự kiểm tra ràng buộc này.

---

## Models đang sử dụng

| Module | Model | Params | Nguồn (HF repo / local) | Vai trò | File cấu hình |
|---|---|---|---|---|---|
| _(chưa có)_ | | | | | |

## Retrieval / Knowledge base settings

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| Embedding model dùng cho candidate retrieval | | |
| Index type (FAISS/BM25/hybrid...) | | |
| Top-k candidates trả về | | |

## Tham số pipeline

| Tham số | Giá trị mặc định | Module | Ghi chú |
|---|---|---|---|
| | | | |

## Biến môi trường / đường dẫn quan trọng

| Tên | Ý nghĩa | Giá trị mặc định |
|---|---|---|
| | | |

---

_Cập nhật lần cuối: (chưa có thay đổi code)_
