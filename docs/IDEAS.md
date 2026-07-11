# Ý tưởng & Planning

File này dùng để hai bên (bạn + Claude) planning trực tiếp: ý tưởng đang theo đuổi, ý tưởng đã thử và lý do giữ/bỏ. Đây là nguồn "trí nhớ" chính của dự án — khi bắt đầu 1 phiên làm việc mới, đọc file này trước để nắm lại bối cảnh thay vì đọc lại toàn bộ code.

Xem thêm: [TASK_SPEC.md](TASK_SPEC.md) (đề bài), [EDA_FINDINGS.md](EDA_FINDINGS.md) (quan sát dữ liệu), [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) (tham số đang dùng), [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) (kết quả).

---

## Trạng thái hiện tại

Giai đoạn: **đã có baseline Tier 0 chạy end-to-end** (exp_0001_baseline). Nền tảng xong: eval harness (validate = 1.0 trên ví dụ đề), I/O + offset, KB matcher, pipeline sinh submission hợp lệ (100 file/32s). **Đang chờ nhãn dev** để có điểm số thật (nhãn nháp đã sinh, chờ người sửa). Lộ trình 4 tầng bên dưới; nguyên tắc: mỗi bước là 1 experiment đo được.

## Câu hỏi mở / TODO cần quyết định

- [x] **[ưu tiên #1]** Eval harness `src/eval/` — DONE (metric WER+Jaccard+weighted candidates, validate = 1.0 trên ví dụ đề, `tests/test_metric.py`).
- [~] **[ưu tiên #2]** Dev set: 15 file đã chọn (`data/labeled/SELECTION.md`). Nhãn **nháp** đã sinh (`data/labeled/ground_truth_draft/`); **còn lại: người sửa → `data/labeled/ground_truth/`** rồi chạy `scripts/run_eval.py` để có điểm baseline thật.
- [ ] **Synthetic train phải phủ cùng feature với dev set** (nhất là token dính liền + code-switching) — spec trong `data/labeled/SELECTION.md`. BTC input không dùng train → feature hiếm (freeform/markdown/N/A) phải chèn bằng code khi sinh data.
- [x] Nguồn ICD-10/RxNorm — đã tải & build `processed/` (xem `knowledge_base/README.md`).
- [ ] Kiến trúc tổng thể: **modular pipeline** (NER→assertion→normalization) hay **end-to-end LLM**? → xu hướng chọn modular (dễ debug/đo từng khối, kiểm soát offset), LLM chỉ chèn ở khối nào chứng minh có lợi. Chốt sau khi có baseline Tier 0–1.
- [ ] Model self-host cho phần LLM/NER — ⚠️ **ngân sách 9B là TỔNG cho toàn pipeline** (mọi model local cộng lại ≤9B, không phải mỗi model). Ứng viên NER encoder `PhoBERT`(~135M)/`XLM-R`/`ViHealthBERT`; LLM sinh `Qwen2.5-7B`/`Vistral-7B`/`SeaLLM-7B`; embedding + reranker cũng tính vào ngân sách. Vd 1 LLM 7B + PhoBERT 135M + embedder 560M ≈ 7.7B (OK); 2 model 7B (14B) là VI PHẠM. Cần benchmark trên dev set trong giới hạn tổng này.
- [ ] Chiến lược retrieval cho candidate mapping (BM25 / dense embedding / hybrid + reranker) — phần "RAG" trọng số cao nhất (0.4).
- [ ] Chiến lược sinh synthetic data để fine-tune (tự sinh note + nhãn từ KB, hoặc weak-labeling bằng rule rồi review).
- [ ] Xử lý `THUỐC`: giữ nguyên cả liều (`metoprolol 25mg po bid`) hay tách hoạt chất+hàm lượng khi map RxNorm? Ảnh hưởng cả text_score (span) lẫn candidates_score.

---

## Ý tưởng đang theo đuổi — lộ trình 4 tầng (cơ bản → nâng cao)

> Triết lý: mỗi tầng phải chạy được end-to-end và sinh submission hợp lệ, để luôn có "phao" điểm số và đo được cải tiến. Không nhảy thẳng lên tầng cao khi chưa có baseline + eval.

### Nền tảng chung (làm trước mọi tầng — "infrastructure")

- **Eval harness** (`src/eval/`): implement đúng công thức metric để tự chấm trên `data/labeled/`. Đây là điều kiện tiên quyết.
- **Dev set** (`data/labeled/`): gán nhãn tay ~15–20 file đa dạng.
- **I/O + offset utility**: đọc `.txt` → sinh `.json` đúng format; hàm tìm `position` (offset ký tự) của span trên **raw text gốc** (chú ý nhiễu token dính liền — xem `EDA_FINDINGS.md` §2). Bước làm sạch (nếu có) phải giữ ánh xạ offset về bản gốc.
- **KB index**: nạp `icd10_vn.csv` + `rxnorm_terms.csv`, dựng index tra cứu (exact dict + fuzzy + sau này là vector).

### Tier 0 — Baseline rule-based + dictionary ✅ ĐÃ TRIỂN KHAI (exp_0001_baseline)

- **NER** (`src/extraction`): heuristic section + bullet + cue nội dung; regex `KẾT_QUẢ_XÉT_NGHIỆM`; drug detection theo route/drug_vocab; bỏ section tường thuật để giữ precision.
- **Assertion** (`src/assertion`): rule section-based `isHistorical`, cue phủ định (lọc false-friend) `isNegated`, cue người nhà `isFamily` (conservative).
- **Candidates** (`src/normalization/kb.py`): fuzzy RapidFuzz với KB — ICD `token_set_ratio`, RxNorm `token_sort_ratio` (ưu tiên clinical drug đúng liều).
- **Trạng thái**: chạy end-to-end, sinh submission hợp lệ. **Điểm: PENDING_GOLD** (chờ nhãn dev).
- **Hạn chế đã lộ** (→ Tier 1): recall thấp do bỏ văn xuôi; candidate thuốc sai granularity; ICD map tên chung vào mã chuyên biệt; tên lay ("hen suyễn") không khớp. Chi tiết: `experiments/exp_0001_baseline/notes.md`.
- **Next**: (1) người sửa nhãn dev → chấm điểm thật → biết khối nào yếu nhất; (2) từ đó quyết định điểm vào Tier 1 (NER fine-tuned hay cải thiện rule + candidate trước).

### Tier 1 — NER fine-tuned + retrieval có học (mục tiêu: nâng recall/độ chính xác NER & mapping)

- **NER + type**: fine-tune token-classification encoder tiếng Việt (`PhoBERT`/`XLM-R`/`ViHealthBERT`, ≤9B) trên dev set + synthetic data; BIO tagging cho 5 type. Xử lý được biến thể ngôn ngữ tốt hơn dictionary.
- **Assertion**: classifier riêng (encoder) trên span + context window, hoặc giữ rule Tier 0 nếu đã đủ tốt (đo để quyết định).
- **Candidates (RAG lõi)**: hybrid retrieval — BM25 (lexical, mạnh cho tên thuốc EN/mã) + dense embedding (đa ngôn ngữ, mạnh cho paraphrase VN) → hợp nhất → **cross-encoder reranker** chọn top-k. Đây là nơi trọng số 0.4 được quyết định.
- **Ưu điểm**: tổng quát hoá tốt hơn rule. **Nhược điểm**: cần dữ liệu train (→ phụ thuộc synthetic data), cần GPU, cần kiểm soát offset khi tokenize.

### Tier 2 — LLM self-host sinh trực tiếp (extraction + assertion 1 lượt)

- **LLM ≤9B** (`Qwen2.5-7B`/`Vistral-7B`/`SeaLLM-7B`) sinh trực tiếp danh sách khái niệm + type + assertion theo schema JSON (few-shot / fine-tune), có **post-process bắt buộc**: căn lại `position` về offset raw (LLM không đáng tin ở việc đếm ký tự), validate type/schema.
- **Candidates**: LLM đề xuất tên chuẩn hoá → đưa vào retrieval Tier 1 (LLM không tự bịa mã, chỉ chuẩn hoá tên để tra KB → tránh hallucination mã ICD/RxNorm).
- **Ưu điểm**: mạnh với văn bản nhiễu, code-switching, suy luận assertion ngữ cảnh. **Nhược điểm**: chậm, khó ép đúng offset, rủi ro hallucination → phải có lớp verify bằng KB + rule.

### Tier 3 — Hybrid / ensemble / agentic (mục tiêu: đẩy trần điểm)

- **Ensemble**: kết hợp NER encoder (Tier 1) cho span + LLM (Tier 2) cho assertion/normalization; vote/hợp nhất theo độ tin cậy.
- **Agentic reasoning** cho ontology: với chẩn đoán/thuốc khó, agent truy vấn KB nhiều bước (mở rộng đồng nghĩa, xét mã cha/con ICD-10, lọc theo cờ "không dùng làm bệnh chính") → chọn candidate tốt hơn.
- **Synthetic data pipeline**: sinh note giả lập từ KB (đảo ngược: chọn mã → sinh câu VN) để fine-tune NER/LLM ở quy mô lớn.
- **Self-consistency / reranking nâng cao**, calibration ngưỡng assertion theo phân tích lỗi trên dev set.
- **Ưu điểm**: trần điểm cao nhất. **Nhược điểm**: phức tạp, dễ overfit dev set nhỏ, chi phí thời gian lớn → chỉ làm khi Tier 1–2 đã ổn và còn thời gian.

---

## Ý tưởng đã thử / đã loại bỏ

> Mỗi mục nên có: mô tả ngắn, ưu điểm, nhược điểm, kết quả (score nếu có), lý do bỏ — để tránh thử lại hướng đã biết không hiệu quả.

_(chưa có — sẽ điền khi 1 hướng bị dừng/thay thế sau experiment thực tế)_
