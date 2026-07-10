# Hướng dẫn làm việc trong repo này

Repo này giải bài thi: NER + chuẩn hoá khái niệm y tế (ICD-10/RxNorm) + suy luận assertion trên văn bản y khoa tiếng Việt tự do. Đọc [`docs/TASK_SPEC.md`](docs/TASK_SPEC.md) để nắm đề bài đầy đủ trước khi làm bất kỳ việc gì trong repo.

File này dành cho cả người (teammate mới join) lẫn LLM agent (Claude Code, Codex...) được giao làm việc trong repo — mục tiêu là hiểu được vai trò từng thư mục và quy tắc tương tác mà không cần đọc hết code.

## Quy tắc bắt buộc

- **Ràng buộc đề bài, không được vi phạm**: nếu dùng LLM/agent trong pipeline, model phải **self-host, tối đa 9B params, không được gọi API ngoài** (xem `docs/TASK_SPEC.md`). Áp dụng nguyên tắc này cho toàn bộ pipeline: mọi thứ chạy offline, không phụ thuộc mạng lúc inference.
- **`TASK/` chỉ đọc, không sửa** — đây là đề bài gốc do BTC cung cấp.
- **`data/raw/input/` là tập test của BTC, không có ground truth** — không dùng để train, không tự gán nhãn rồi coi là "đúng tuyệt đối". Muốn tự chấm điểm, dùng `data/labeled/`.
- **`knowledge_base/rxnorm/raw/` bị gitignore** (~2.1GB, nhiều file >100MB — vượt giới hạn cứng của GitHub) — nếu clone repo về mà thiếu, đọc `rxnorm/raw/SOURCE.md` để biết link tải + hướng dẫn, đừng tự bịa dữ liệu thay thế. `knowledge_base/icd10/raw/` thì được track bình thường (nhỏ, ~22MB). Thứ code thực sự dùng luôn là `knowledge_base/*/processed/*.csv` (luôn có trong git, không cần raw để chạy pipeline).
- **Trước khi bắt đầu 1 task/phiên làm việc mới, đọc `docs/IDEAS.md` trước** — đây là bộ nhớ chính của dự án, tránh việc thử lại hướng đã biết không hiệu quả hoặc đi ngược ý tưởng đang theo đuổi.

## Cấu trúc repo — vai trò từng phần

| Thư mục | Vai trò | LLM nên đọc/ghi khi nào |
|---|---|---|
| `TASK/` | Đề bài gốc + metric, nguyên văn từ BTC | Chỉ đọc, không sửa |
| `docs/` | Tài liệu tổng hợp — xem chi tiết bên dưới | Đọc đầu phiên làm việc; ghi sau khi có quyết định/kết quả mới |
| `knowledge_base/` | ICD-10 (`icd10/`) + RxNorm (`rxnorm/`) — nguồn tri thức cho candidate mapping | Đọc từ `*/processed/*.csv` (luôn có trong git). `rxnorm/raw/` gitignore (~2.1GB) — không có sẵn khi clone, xem `SOURCE.md` nếu cần tự build lại |
| `data/raw/` | 100 file `.txt` test của BTC, không nhãn | Chỉ đọc, dùng làm input cuối cùng để sinh submission |
| `data/labeled/` | Tập dev tự gán nhãn (input + ground_truth) | Đọc để chạy `src/eval/`; ghi khi gán nhãn thêm sample mới |
| `data/synthetic/` | Dữ liệu tự sinh thêm để train/fine-tune | Ghi khi có script sinh data mới; đọc khi train |
| `models/` | Model weights/checkpoint dùng chung giữa các experiment | Weight thật bị gitignore — đọc `SOURCE.md` để biết cách tải/tái tạo |
| `src/` | **Code chính** — pipeline chạy thật (`extraction/`, `normalization/`, `assertion/`, `eval/`) | Đây là nơi implement/sửa logic bài toán |
| `notebooks/` | EDA, soi lỗi từng sample, thử nhanh ý tưởng | Không cần sạch — không refactor thành `src/` trừ khi ý tưởng đã chứng minh hiệu quả |
| `experiments/` | Mỗi lần chạy pipeline = 1 folder (`config.yaml`, `predictions/`, `metrics.json`) | **Mọi lần chạy thử nghiệm phải tạo 1 folder mới ở đây**, không ghi đè experiment cũ |
| `references/` | Paper/code SOTA (RAG, reasoning, ontology) pull về để đọc tham khảo | Chỉ đọc để lấy ý tưởng — **không import trực tiếp vào `src/`**, không phải code chạy được của dự án |
| `scripts/` | Tiện ích: ETL knowledge base, đóng gói submission `output.zip`, chạy eval hàng loạt | Chạy khi cần build lại `processed/` hoặc đóng gói nộp bài |

### Vài điểm dễ nhầm

- `experiments/` chứa **kết quả** (predictions + metrics của từng lần chạy cụ thể), khác với `src/` là **code** — không lẫn 2 khái niệm này. Khi được yêu cầu "chạy thử nghiệm X", nghĩa là: chạy pipeline trong `src/` với 1 cấu hình, lưu output vào `experiments/exp_XXXX_<tên>/`, không phải sửa trực tiếp code trong `src/` rồi thôi.
- `references/` là thư viện tham khảo thụ động — nếu 1 kỹ thuật trong đó đáng áp dụng, viết lại/implement trong `src/` theo phong cách của dự án, không copy nguyên code từ `references/` vào `src/`.
- Dữ liệu "thật" luôn nằm ở `processed/` (đã lọc, gọn, track trong git); `raw/` chỉ là kho lưu nguồn gốc, nặng, gitignored.

## `docs/` — chi tiết cách tương tác

Đây là bộ nhớ và "nguồn sự thật" của dự án — đọc để nắm toàn bộ ý tưởng/tiến độ mà không cần đọc code.

### `docs/TASK_SPEC.md`
Bản tóm tắt đề bài + công thức chấm điểm. Chỉ đọc. Nếu đề bài gốc trong `TASK/` có thay đổi thật (BTC cập nhật), cập nhật file này cho khớp.

### `docs/IDEAS.md` — nơi lên kế hoạch, **đọc đầu tiên mỗi phiên làm việc**
- Khi bắt đầu 1 ý tưởng/hướng tiếp cận mới → thêm mục vào **"Ý tưởng đang theo đuổi"** (mô tả, vì sao chọn, trạng thái, link experiment liên quan).
- Khi 1 ý tưởng bị dừng/thay hướng (dù đã chạy experiment hay chưa) → chuyển xuống **"Ý tưởng đã thử/loại bỏ"**, ghi rõ ưu điểm, nhược điểm, kết quả (score nếu có), lý do bỏ, bài học rút ra. **Không xoá ý tưởng cũ** — mục đích của phần này là để không thử lại hướng đã biết không hiệu quả.
- Mục "Câu hỏi mở/TODO" dùng để track quyết định chưa chốt (nguồn dữ liệu, kiến trúc, model...) — tick `[x]` khi đã quyết xong, có thể ghi thêm TODO mới khi phát sinh.

### `docs/CONFIG_REFERENCE.md`
Mỗi khi **thêm hoặc đổi model/tham số quan trọng trong `src/`**, phải cập nhật bảng tương ứng ở đây (model dùng, params, retrieval settings, tham số pipeline). Mục tiêu: đọc file này là biết code đang chạy gì, không cần lục `src/`. Nhắc lại ràng buộc self-host ≤9B params để tự kiểm tra khi thêm model mới.

### `docs/EXPERIMENTS_LOG.md`
Sau **mỗi lần chạy experiment mới** trong `experiments/`, thêm 1 dòng vào bảng (ID, mô tả, text_score/assertions_score/candidates_score/final_score, nhận xét, link folder). Đây là bảng roll-up để so sánh nhanh, không cần mở từng folder `experiments/exp_XXXX/`.

## Workflow điển hình (cho LLM agent khi được giao 1 task)

1. Đọc `docs/IDEAS.md` (bối cảnh/ý tưởng hiện tại) + `docs/TASK_SPEC.md` (đề bài) nếu chưa nắm.
2. Code/sửa logic trong `src/`.
3. Chạy pipeline trên `data/labeled/` (hoặc `data/raw/input/` nếu chỉ để sinh submission), dùng `src/eval/` để tự chấm nếu có ground truth.
4. Lưu output vào 1 folder mới trong `experiments/exp_XXXX_<tên>/` (config + predictions + metrics).
5. Cập nhật `docs/EXPERIMENTS_LOG.md` (luôn), `docs/CONFIG_REFERENCE.md` (nếu đổi model/tham số), `docs/IDEAS.md` (nếu ý tưởng thay đổi hướng hoặc bị loại bỏ).
