# Ý tưởng & Planning

File này dùng để hai bên (bạn + Claude) planning trực tiếp: ý tưởng đang theo đuổi, ý tưởng đã thử và lý do giữ/bỏ. Đây là nguồn "trí nhớ" chính của dự án — khi bắt đầu 1 phiên làm việc mới, đọc file này trước để nắm lại bối cảnh thay vì đọc lại toàn bộ code.

Xem thêm: [TASK_SPEC.md](TASK_SPEC.md) (đề bài), [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) (tham số đang dùng), [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) (kết quả).

---

## Trạng thái hiện tại

_(chưa có ý tưởng nào được chốt — cập nhật khi bắt đầu thiết kế pipeline)_

## Câu hỏi mở / TODO cần quyết định

- [ ] Gán nhãn 1 tập dev nhỏ vào `data/labeled/` để `src/eval/` có cơ sở tự chấm điểm trước khi nộp
- [x] Nguồn ICD-10/RxNorm — đã tải: RxNorm Full Release (`knowledge_base/rxnorm/raw/`), ICD-10 tiếng Việt Bộ Y tế Thông tư 06/2026/TT-BYT (`knowledge_base/icd10/raw/`)
- [ ] Viết script parse `icd10/raw/06-byt-kem.pdf` (1271 trang, 29 cột) và lọc `rxnorm/raw/rrf/RXNCONSO.RRF` → `processed/` (xem TODO trong `knowledge_base/README.md`)
- [ ] Kiến trúc tổng thể: pipeline theo module riêng (NER → normalization → assertion) hay 1 model/agent xử lý end-to-end?
- [ ] Model self-host nào dùng cho phần LLM/agent (giới hạn ≤ 9B params, không API ngoài)
- [ ] Chiến lược retrieval cho candidate mapping (dense embedding? BM25? hybrid?) — đây là phần "RAG" chính của bài toán
- [ ] Chiến lược sinh thêm synthetic data để train/fine-tune

---

## Ý tưởng đang theo đuổi

### [Ý tưởng #1 — tên ý tưởng]

- **Mô tả**:
- **Vì sao chọn**:
- **Trạng thái**: đang thử nghiệm / chưa bắt đầu
- **Experiment liên quan**: (link tới `experiments/exp_XXXX_.../`)

---

## Ý tưởng đã thử / đã loại bỏ

> Mỗi mục nên có: mô tả ngắn, ưu điểm, nhược điểm, kết quả (score nếu có), lý do bỏ — để tránh thử lại hướng đã biết không hiệu quả.

### [Ý tưởng cũ #0 — ví dụ mẫu, xoá khi có ý tưởng thật]

- **Mô tả**:
- **Ưu điểm**:
- **Nhược điểm**:
- **Kết quả** (nếu đã chạy experiment): final_score = ..., text_score = ..., assertions_score = ..., candidates_score = ...
- **Lý do loại bỏ / tạm dừng**:
- **Bài học rút ra cho hướng sau**:
