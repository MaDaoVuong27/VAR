# Hướng dẫn làm việc trong repo này

Repo này giải bài thi: NER + chuẩn hoá khái niệm y tế (ICD-10/RxNorm) + suy luận assertion trên văn bản y khoa tiếng Việt tự do. Đọc [`docs/TASK_SPEC.md`](docs/TASK_SPEC.md) để nắm đề bài đầy đủ trước khi làm bất kỳ việc gì trong repo.

File này dành cho cả người (teammate mới join) lẫn LLM agent (Claude Code, Codex...) được giao làm việc trong repo — mục tiêu là hiểu được vai trò từng thư mục và quy tắc tương tác mà không cần đọc hết code.

## Quy tắc bắt buộc

- **Ràng buộc đề bài, không được vi phạm**: nếu dùng LLM/agent trong pipeline, model phải **self-host, không gọi API ngoài**, và **TỔNG tham số của TẤT CẢ model local cộng lại ≤ 9B** (không phải mỗi model ≤9B — xem `docs/TASK_SPEC.md`). Áp dụng nguyên tắc này cho toàn bộ pipeline: mọi thứ chạy offline, không phụ thuộc mạng lúc inference.
- **LIÊM CHÍNH — output nộp bài phải do CODE tự động sinh ra, tái tạo được, KHÔNG được**: (1) hard-code kết quả theo từng file test; (2) dùng LLM mạnh/API ngoài (Claude, Codex, GPT...) để **suy luận ra output**; (3) người gán nhãn tay tập test rồi nộp. → Đây là gian lận, sẽ bị loại (BTC re-run source trên private test để kiểm). Dùng LLM ngoài để **viết code giải pháp** thì được; **sinh ra output** thì không. Mọi thứ trong `data/labeled/ground_truth/` (nhãn dev để tự chấm) **tách rời** khỏi output nộp bài — không được rò rỉ vào pipeline sinh submission.
- **Synthetic data cũng phải tuân luật + nộp kèm**: nộp cả code sinh synthetic **và** file synthetic gốc (BTC re-run không tái tạo y hệt do ngẫu nhiên/LLM sampling — code chỉ để tham khảo cách làm). Vì code sinh synthetic bị BTC review → **khâu sinh synthetic chỉ được dùng model self-host ≤9B, không API ngoài** (không dùng Claude/GPT sinh data train). Chi tiết: `docs/DATA_PLAN.md` §PHẦN 2.
- **`TASK/` chỉ đọc, không sửa** — đây là đề bài gốc do BTC cung cấp.
- **`data/raw/input/` là tập test của BTC → CHỐNG DATA LEAKAGE**: (1) KHÔNG train trên chúng; (2) KHÔNG chia train/test từ 100 file này; (3) KHÔNG lấy chúng làm câu gốc/template để sinh synthetic — **kể cả chỉ "mượn cấu trúc câu"** (model sẽ học phân phối test = leakage). Synthetic phải từ nguồn của TA (template tự viết / KB / corpus ngoài hợp lệ). Được phép: hand-label một subset → `data/labeled/` để **tự chấm/chọn model** (không rò vào output nộp bài).
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

### `docs/EDA_FINDINGS.md`
Quan sát đặc điểm dữ liệu test (cấu trúc, nhiễu, phân bố assertion, hệ quả từ metric) + checklist EDA cần chạy bằng code. Đọc khi cần hiểu "dữ liệu trông thế nào" trước khi thiết kế/sửa NER hay rule. Cập nhật khi có quan sát mới (vd sau khi gán nhãn dev set, hoặc phân tích lỗi experiment).

### `docs/IDEAS*.md` + `docs/DATA_PLAN.md` — kế hoạch, **đọc `IDEAS.md` đầu tiên mỗi phiên**
- **`docs/IDEAS.md`** = trang chủ chiến lược: so sánh 3 hướng giải, kiến trúc tổng, ngân sách 9B, thứ tự thực thi, "Câu hỏi mở/TODO", "Ý tưởng đã thử/loại bỏ". Đọc file này để nắm hướng tổng thể.
- **`docs/IDEAS_1.md`** (Hướng A: fine-tune NER), **`docs/IDEAS_2.md`** (Hướng B: RAG/entity-linking/KG), **`docs/IDEAS_3.md`** (Hướng C: multi-agent) — báo cáo chi tiết từng hướng. 3 hướng là **3 lớp của cùng pipeline**, không loại trừ nhau (A+B bắt buộc, C tùy chọn).
- **`docs/DATA_PLAN.md`** = làm sạch + sinh synthetic data (nền chung cho mọi hướng có học).
- Quy tắc cập nhật: ý tưởng mới → thêm vào doc hướng tương ứng; ý tưởng bị loại → mục "Đã thử/loại bỏ" trong `IDEAS.md` (ghi ưu/nhược/score/bài học, **không xoá**); quyết định đã chốt → tick `[x]` ở "Câu hỏi mở/TODO".

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
