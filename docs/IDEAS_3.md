# IDEAS_3 — Hướng C: Multi-agent (lớp điều phối / đẩy trần điểm)

> 1 trong 3 hướng. Điều hướng + so sánh: [IDEAS.md](IDEAS.md). Liên quan: [IDEAS_1.md](IDEAS_1.md) (NER), [IDEAS_2.md](IDEAS_2.md) (candidate).

## 0. Định vị: đây là LỚP ĐIỀU PHỐI, không phải bộ trích xuất thay thế

Multi-agent **không thay** NER encoder (hướng A) hay retrieval (hướng B) — nó **điều phối** chúng + thêm LLM để suy luận/kiểm tra. Đặt ở đây vì: (1) phức tạp nhất, (2) chỉ đáng làm khi khối lõi A+B đã chạy tốt, (3) rủi ro chi phí/ràng buộc cao nhất. Là hướng để **đẩy trần điểm**, không phải để đạt điểm sàn.

## 1. Hai cách chia agent

### 1a. Chia theo STAGE (pipeline agents)
`Extraction agent` → `Assertion agent` → `Linking agent` → `Verification/Eval agent`. Mỗi agent 1 nhiệm vụ hẹp, dễ debug/đo. **Verification agent** đặc biệt giá trị: kiểm tra output có hợp lệ không (span khớp raw? thuốc map được RxNorm? type hợp lý?) → sửa lỗi trước khi nộp. Đây là "self-consistency" nhẹ.

### 1b. Chia theo TYPE (ý tưởng user — agent riêng cho từng loại khái niệm)
`Symptom agent`, `Drug agent`, `Diagnosis agent`, `Test-name agent`, `Result agent` — mỗi agent chỉ quét 1 type trong 1 sample.
- **Ưu điểm**: prompt cực tập trung (agent thuốc chỉ cần biết đặc điểm tên thuốc + liều), ít nhầm lẫn giữa type, dễ nhét kiến thức chuyên biệt (agent bệnh có sẵn tri thức ICD, agent thuốc có RxNorm), song song hoá được.
- **Nhược điểm**: (1) **chi phí ×5** lần gọi LLM/sample (100 file × 5 agent — chậm); (2) **ranh giới type chồng lấn** — 1 span có thể bị 2 agent cùng nhận (vd "đái tháo đường" là chẩn đoán nhưng "tăng đường huyết" giữa chẩn đoán/kết quả) → cần bước hợp nhất/trọng tài; (3) khó đảm bảo **phủ hết** (không agent nào nhận thì mất).
- **Đánh giá**: ý tưởng hay về precision (mỗi type 1 chuyên gia) nhưng tốn kém. **Hợp lý nếu**: dùng chung 1 LLM self-host, prompt khác nhau, chạy tuần tự — và chỉ trên các type khó (thuốc/chẩn đoán cần candidate) thay vì cả 5.

## 2. Ràng buộc phải tính (quan trọng)

- **9B TỔNG**: nhiều agent KHÔNG có nghĩa nhiều model. Phải dùng **cùng 1 LLM self-host** (vd Qwen2.5-7B) đóng nhiều vai qua prompt khác nhau → tổng tham số vẫn = 1 model. Chạy 5 model 7B song song = 35B = VI PHẠM.
- **Tốc độ**: LLM 7B trên RTX 3060 (12GB, quantized) ~ vài giây/lần gọi. 100 file × nhiều agent × nhiều khái niệm → có thể hàng giờ. A100 của teammate giảm tải nhưng lúc BTC re-run trên máy của họ vẫn phải chạy được → không nên phụ thuộc agentic quá nặng.
- **Offset**: LLM không đáng tin khi đếm ký tự → mọi output agent phải qua hậu xử lý căn `position` về raw (như đã ghi ở Tier 2 cũ).

## 3. SOTA & liên hệ

- [OEMA — Ontology-Enhanced Multi-Agent cho zero-shot clinical NER (2025)](https://arxiv.org/pdf/2511.15211): multi-agent + ontology, đúng tinh thần chia vai + bơm tri thức chuẩn (ICD/RxNorm) vào agent. Đáng đọc kỹ cho cách phối hợp agent + ontology.
- **KARMA** (user nêu — multi-agent cho knowledge graph enrichment): ý tưởng nhiều agent LLM làm giàu KG. Liên quan gián tiếp: nếu ta xây KB/graph (hướng B), agent có thể dùng để **mở rộng synonym/quan hệ** khi build KB offline (không phải lúc inference) — an toàn hơn là agent chạy runtime. *(Chưa verify chi tiết paper — dùng ở mức ý tưởng.)*
- Verification/self-consistency: nhiều lời giải LLM rồi vote — tăng độ tin, nhưng ×N chi phí.

## 4. Khuyến nghị (thực dụng)

1. **Không bắt đầu bằng full agent swarm.** Trước hết A (NER) + B (retrieval) phải cho điểm tốt.
2. Agent đầu tiên đáng làm là **Verification agent** (rẻ, giá trị cao): sau khi pipeline A+B ra output, 1 lượt LLM kiểm tra & sửa lỗi rõ ràng (span rác, type sai, thiếu candidate). Không cần ×5 agent.
3. Chia theo type chỉ nên thử **sau**, và chỉ cho 2 type nặng candidate (THUỐC, CHẨN_ĐOÁN), dùng chung 1 LLM.
4. Đo mọi thứ trên dev gold — agentic dễ tưởng "thông minh" nhưng không chắc tăng điểm; phải chứng minh bằng số.

## 5. Thứ tự thực thi
1. (sau khi A+B ổn) **Verification agent** 1 lượt → đo delta.
2. Thử **type-specialized agent** cho THUỐC + CHẨN_ĐOÁN → đo.
3. Self-consistency/vote nếu còn budget thời gian.

## Nguồn tham khảo
- [OEMA: Ontology-Enhanced Multi-Agent Collaboration for Zero-Shot Clinical NER (2025)](https://arxiv.org/pdf/2511.15211)
- [Clinical Coding with LLM Agents](https://aiforhealthcare.substack.com/p/clinical-coding-with-llm-agents)
