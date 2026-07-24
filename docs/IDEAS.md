# IDEAS — Chiến lược tổng & điều hướng kế hoạch

Trang chủ của phần planning. Đọc file này để nắm **hướng giải tổng thể + vì sao**, rồi vào các doc chi tiết theo hướng. Bộ nhớ chính của dự án — đọc đầu mỗi phiên.

Xem thêm: [TASK_SPEC.md](TASK_SPEC.md) (đề+metric), [EDA_FINDINGS.md](EDA_FINDINGS.md) (dữ liệu), [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) (kết quả), [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) (tham số).

## Bản đồ docs kế hoạch

| Doc | Nội dung |
|---|---|
| **IDEAS.md** (đây) | Chiến lược tổng, so sánh 3 hướng, khuyến nghị, thứ tự thực thi |
| [IDEAS_1.md](IDEAS_1.md) | **Hướng A** — Fine-tune NER encoder + ensemble (khối extraction) |
| [IDEAS_2.md](IDEAS_2.md) | **Hướng B** — RAG / Entity Linking / Knowledge Graph (khối candidate, 0.4) |
| [IDEAS_3.md](IDEAS_3.md) | **Hướng C** — Multi-agent (lớp điều phối, đẩy trần) |
| [DATA_PLAN.md](DATA_PLAN.md) | Làm sạch dữ liệu + **sinh synthetic data** (nền cho A/B/C) |
| [SYNTHETIC_V5_PLAN.md](SYNTHETIC_V5_PLAN.md) | 🆕 **Kế hoạch xây lại synthetic v5** (quality-first ~1.000 doc) + chốt boundary convention + TODO theo phase |
| [TRAINING_WORKFLOW_PLAN.md](TRAINING_WORKFLOW_PLAN.md) | 🆕 **Workflow training 3 khối** (NER / assertion / candidate) — áp OpenBioNER description vào reranker; description dựng RULE từ KB, không cần LLM |

---

## 1. Ta đang ở đâu (dữ kiện, không phỏng đoán)

- **Baseline Tier 0** (rule/fuzzy, 0 model): điểm THẬT từ BTC = **16.34/100** (text 19.2, assert 22.5, cand 9.6). Chi tiết `EXPERIMENTS_LOG.md`.
- **exp_0003 — Tier 1 NER (XLM-R fine-tune synthetic)** ✅ **ĐIỂM THẬT BTC = 22.18 (+5.84 vs baseline 16.34)** — **vẫn là BEST thật**. text 28.63 (+9.45), assert 31.03 (+8.58), cand 10.71 (+1.08).
  - **candidates vẫn thấp nhất (10.71, weight 0.4)** → **SapBERT là đòn bẩy lớn nhất** còn lại.
- **⭐ exp_0007 (NER v2 + SapBERT-only abstain th=0.7) = ĐIỂM THẬT BTC 23.84430 — BEST HIỆN TẠI** (+1.66 vs exp_0003). Nguyên văn: `WER 72.2255 · J_assertion 30.1416 · J_candidates 16.1736`. → **cand 10.71 → 16.1736 (+51%)**: SapBERT thắng fuzzy dứt khoát, **câu hỏi treo từ exp_0004 đã khép lại**. text/assert tụt nhẹ (~0.9 mỗi cái) do `split_newlines`.
- 🔓 **Giải mã được bảng chỉ số BTC**: `text_score = 100 − WER`, nên **mỗi lượt nộp cho 3 phép đo chứ không phải 1**. Xem [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §Giải mã.
- **⭐ exp_0010 (NER XLM-R-LARGE trên synthetic v3) = 28.62340** (+4.78 vs exp_0007). Nâng NER base + sửa 3 bug synthetic (glue chết, doc quá ngắn, filler hỏng) + fix sliding-window train cứu 45.7% nhãn → text/assert/cand tăng đều.
- **exp_0013 (NER v4-mix: template 6k + Qwen-prose 2830) = 31.78610** (+3.16 vs exp_0010). Prose do LLM self-host sinh đẩy CẢ 3: text +4.62, cand +4.12, assert +0.43. → **Văn xuôi tự nhiên là đòn bẩy lớn — model học bắt khái niệm ngoài cấu trúc bullet.**
- **exp_0018 (v4-mix + rerank off-the-shelf, KHÔNG train) = 31.90790** (+0.12 vs exp_0013).
- **exp_0023 (v4-mix + rerank + rule isHistorical vá) = 31.97440** (+0.22 vs exp_0018 — thật nhưng nhỏ hơn NHIỀU dev đã báo, ~13× nhỏ hơn).
- **🏆 exp_0022 (v4-mix + rerank + ASSERTION CLASSIFIER) = BTC 32.79790 — BEST HIỆN TẠI** (+2.97 J_assertion, +0.89 final vs exp_0018). ⚠️ **Dev từng nói classifier THUA rule (0.6365 vs 0.6607) — SAI HƯỚNG hoàn toàn**, phát hiện muộn do ban đầu 2 kết quả nộp bị báo nhầm nhãn. Đây là đảo ngược quyết định "giữ rule, bỏ classifier" đã chốt trước đó. Chi tiết + giả thuyết nguyên nhân: [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §ĐẢO NGƯỢC LỚN.
- **exp_0008 (ICD k=2) = 23.05 < exp_0007 23.84** → gold BTC chủ yếu 1 mã/concept. **Chốt k=1.**
- **exp_0012 (sap_th 0.5, coverage 99%) = 26.32 < exp_0010 28.62** → **ABSTAIN SINH ĐIỂM THẬT** (cand 19.04→13.29 khi phủ mã cho span rác). **Chốt: giữ sap_th cao (0.7+), abstain khi sim thấp.** Xem §exp_0012 EXPERIMENTS_LOG.
- ⚠️ **Từng "sửa" metric rồi HOÀN TÁC** (2026-07-15): đổi concept-thừa từ `J(∅,∅)=1` thành 0, dựa trên độ-khớp-tuyệt-đối với BTC → SAI, làm dev mù trước exp_0010 vs exp_0012. **Bài học: chỉ chỉnh metric theo XẾP HẠNG, không theo giá trị tuyệt đối.**
- ✅ **Quy luật dùng dev (kiểm chứng 4/4 + cứu 1 quyết định thật ở exp_0013)**: **span GIỐNG nhau (chỉ đổi matcher) → dev xếp hạng ĐÚNG; span KHÁC → dev sai, và sai CÓ HƯỚNG** (giảm over-predict làm dev cand tụt dù cand thật tăng). Khi đổi NER model → **bóc tách numerator** (khớp-gold-thật vs credit-ảo-abstain) thay vì tin dev tổng. `text_score` luôn so trực tiếp được (không có cơ chế abstain).
- **Đã loại bỏ**: dense retrieval off-the-shelf (exp_0002) — embedder general quá yếu (xem cuối trang).
- 🆕🚨 **BTC cấp đề TEST TURN 2 (2026-07-23) — test set THẬT SỰ đổi** (khác "nâng cấp giả" 07-16,
  lần đó byte-for-byte giống hệt). 0/100 file trùng nội dung với test cũ. Chi tiết:
  [EDA_FINDINGS.md](EDA_FINDINGS.md) §0 + [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §turn 2.
  **exp_0026 (v4_mix, model y hệt exp_0022) chấm trên test turn 2 = 22.7685**, tụt **10.03 điểm**
  so với chính nó trên test cũ (32.798) — cả 3 thành phần đều tụt, `J_candidates` tụt nặng nhất
  (**−43% tương đối**, 23.47→13.30). Nguyên nhân (đã EDA): văn phong bài giáo dục sức khỏe (khác
  ghi chú lâm sàng), redaction thuốc bằng `***` (30/100 file), nội dung lạc đề chèn giữa case
  (37/100 file), tài liệu dài hơn 54%. **Top 1 leaderboard hiện tại: 40.5.**
  → **`exp_0026` là điểm neo mới** cho mọi so sánh trên test turn 2 (thay `exp_0022` cho test cũ).
- ✅ **Xác nhận phương pháp luận qua dịch chuyển phân phối**: `exp_0027` (v5c) trên CÙNG test turn
  2 = 20.0336, THUA `exp_0026` ở cả 3 thành phần — đúng thứ tự `diagnose_boundary` đã dự đoán
  trên test cũ. Quy luật "so bằng diagnose_boundary trước khi tốn lượt nộp" đáng tin cả khi dữ
  liệu đổi mạnh.
- ❌ **KB-description reranker (exp_0028/0029) + ❌ entity masking A/B (exp_0030) — cả 2 đều KHÔNG
  vượt được cấu hình đang có** (chi tiết dưới §Ý tưởng đã thử). Kết luận sau sprint cuối 2026-07-23:
  **`exp_0026` (v4_mix + boundary-fix + rerank tên trần + assertion classifier) vẫn là cấu hình
  BEST đã xác nhận**, không có ứng viên mới nào thắng nó trong lượt này. PhoBERT ensemble bị chặn
  cứng (tokenizer không hỗ trợ `return_offsets_mapping`, cần VnCoreNLP + code alignment riêng —
  không kịp trong ngân sách thời gian) nên không thử được.
- 🚨 **PHÁT HIỆN QUAN TRỌNG (exp_0031, 2026-07-24): scorer BTC thật dựa vào `position` CHẶT hơn
  nhiều so với model nội bộ của ta.** Zero hết `position` trên chính output đã ăn 22.7685
  (giữ nguyên text/type/candidates/assertions) → dev proxy dự đoán chỉ giảm −3.3%, BTC thật giảm
  **−66%** (final 22.77→~7.73, WER 72.17→100 = mismatch toàn bộ, J_assertion 30.33→0). → **Đầu tư
  vào độ chính xác BOUNDARY của NER có giá trị thật cao hơn con số dev proxy từng cho thấy** — quy
  luật "cùng span → dev xếp hạng đáng tin" vẫn đúng cho so sánh model bình thường, chỉ riêng mức độ
  ẢNH HƯỞNG TUYỆT ĐỐI của lỗi position bị proxy đánh giá thấp. Chi tiết: `EXPERIMENTS_LOG.md`
  §exp_0031, `src/eval/metric.py` docstring điểm 7.

### 🔑 Việc quan trọng nhất tiếp theo
1. ✅ **Đã xong**: exp_0014 (prose-only, xác nhận prose bổ trợ chứ không thay template) + exp_0015 (dense 14830, xác nhận +3.16 của exp_0013 đến từ PROSE chứ không phải giảm template).
2. ❌ **SapBERT fine-tune contrastive — 2 lần thử ĐỀU THẤT BẠI** (naive: dev cand 0.366→0.328; hard-negative: →0.2581, tệ hơn). Cơ chế: contrastive dịch chuyển toàn phổ similarity → threshold cố định 0.7 mất hiệu lực. **Dừng hướng này.** Chi tiết + bài học: [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §exp_0016/exp_0017.
3. ✅ **🏆 exp_0018 (SapBERT retrieval + rerank off-the-shelf bge-reranker-v2-m3, KHÔNG train) = BTC 31.90790 — BEST MỚI** (+0.12 vs exp_0013). Dev đã báo SAI HƯỚNG (0.366→0.333, tụt) — BTC thực tế TĂNG nhẹ (23.16→23.47). Lý do: đây là so sánh cùng-span nhưng **abstain rate giữ nguyên 22%=22%** (khác mọi lần trước, luôn kèm đổi abstain rate) → cơ chế "credit ảo" không chi phối được nữa → dev mất tin cậy cho hiệu ứng nhỏ. **Bài học quan trọng**: quy luật "cùng span → dev tin được" cần thêm điều kiện "VÀ abstain rate cũng đổi đáng kể" — xem chi tiết [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §exp_0018. Cải tiến nhỏ, nhưng đổi default matcher sang rerank vì đây là best đã biết.
4. ❌ **Hybrid BM25∪dense (RRF) — THẤT BẠI** (exp_0021: cand 23.47→23.13, final 31.91→31.77). BM25 thêm nhiễu > tín hiệu; SapBERT dense pool vốn đã tốt. **Dừng hướng BM25.**

### 🏁 Khối candidate đã KHAI THÁC HẾT các hướng rẻ — best = exp_0018 (rerank off-the-shelf trên SapBERT)
Đã thử & loại: SapBERT fine-tune naive (0016), hard-neg (0017), rerank off-the-shelf (**0018 = BEST +0.12**), hybrid BM25 (0021 tệ hơn). **Cấu hình candidate tốt nhất: SapBERT retrieval th=0.7 + rerank bge-v2-m3, KHÔNG BM25, KHÔNG fine-tune.** cand 23.47 vẫn là thành phần thấp nhất nhưng mọi cải tiến rẻ đã cạn. Hướng còn lại cho candidate (đắt, chưa thử): fine-tune reranker cross-encoder trên cặp (span, tên-mã) có nhãn — cần dữ liệu train tốt.

### 🎯 ĐÒN BẨY LỚN NHẤT CÒN LẠI: chuyển sang text/assert + hoàn thiện dev gold
- **text 38.69 (weight 0.3)**: đã cải thiện nhiều nhờ prose, nhưng NER vẫn over-predict (span thừa phạt WER). Chưa thử: hậu xử lý lọc span rác, ensemble multi-seed.
- ⚠️ **ĐẢO NGƯỢC**: ban đầu tưởng exp_0023 (rule vá) = best, sau xác minh lại đúng là **exp_0022 (CLASSIFIER) mới là best (32.79790)**. Rule vá thật có tác dụng (+0.22) nhưng nhỏ hơn nhiều dev báo; classifier — mà dev từng nói THUA — thực ra thắng đậm nhất (+2.97). **Rút lại bài học "vá rule > thay model"** — đó là kết luận sai, dựa trên dev bị fit vào chính sample dùng để chẩn đoán bug. Xem [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §ĐẢO NGƯỢC LỚN.
- **dev gold**: gỡ nút thắt "phải đốt lượt nộp cho mọi câu hỏi biên". Hiện dev mù cho mọi so sánh đổi NER + mọi so sánh candidate khi abstain không đổi.
4. **Hoàn thiện dev gold** (INCOMPLETE — đếm sót occurrence) → dev mới xếp hạng tin cậy khi span khác nhau (NER khác model). Hiện dev chỉ tin được trong cùng họ span/matcher.
5. **Assertion classifier** (assert 36.38, vẫn rule): thay rule bằng model. ⚠️ Nhãn assertion của prose có nhiễu (isNegated ~59% khớp) — cần lọc trước khi train classifier.
4. **Đo exp_0007 trên BTC** — phép thử candidate quyết định (SapBERT vs fuzzy) vẫn chưa được trả lời bằng số thật.

## 2. Phân tích metric-driven → nút thắt gốc

`final = 0.3·text + 0.3·assert + 0.4·candidates`. Điểm hiện tại thấp ĐỀU ở cả 3 → không phải chỉ candidate yếu. Nguyên nhân chung:

> **Nếu NER không bắt được khái niệm thì cả 3 điểm thành phần đều = 0 cho khái niệm đó** — không có text để tính WER, không có assertion, không có candidate.

→ **NER recall (bắt khái niệm bất kể vị trí trong câu) là nút thắt gốc.** Đây là đòn bẩy #1: cải thiện NER kéo lên cả text (0.3) và mở đường cho assert (0.3) + candidate (0.4).

## 3. Insight quan trọng nhất: 3 hướng KHÔNG loại trừ nhau — chúng là 3 LỚP

User nêu 3 hướng (fine-tune NER / RAG-KG / multi-agent) như các lựa chọn. Nhưng nhìn kỹ, chúng **không phải 3 con đường thay thế nhau** mà là **3 lớp của cùng 1 pipeline**:

```
   [ Văn bản thô ]
          │
   ┌──────▼───────┐
   │  HƯỚNG A     │  Extraction: NER encoder tìm span + type   ← nút thắt, BẮT BUỘC
   │  (IDEAS_1)   │
   └──────┬───────┘
          │  spans + types
   ┌──────▼───────┐
   │  HƯỚNG B     │  Normalization: span → mã ICD/RxNorm         ← trọng số 0.4, BẮT BUỘC
   │  (IDEAS_2)   │  (SapBERT retrieval + reranker + ontology)
   └──────┬───────┘
          │  concepts + candidates + assertions
   ┌──────▼───────┐
   │  HƯỚNG C     │  Orchestration: agent điều phối + verify      ← tùy chọn, đẩy trần
   │  (IDEAS_3)   │
   └──────┬───────┘
          ▼
   [ output.json ]
```

- **A là bắt buộc** (giải nút thắt recall).
- **B là bắt buộc** (giải trọng số 0.4 — mà A không đụng tới).
- **C là tùy chọn** — chỉ đáng khi A+B đã tốt, để đẩy trần bằng verify/suy luận.

→ Câu hỏi đúng KHÔNG phải "chọn hướng nào" mà là "**làm A và B cho tốt trước, C sau**". Cả 3 dùng chung [DATA_PLAN.md](DATA_PLAN.md).

## 4. Kiến trúc tổng đề xuất (modular, đo được từng khối)

**Modular pipeline** (không phải 1 LLM end-to-end): NER encoder → assertion → entity-linking retrieval → (tùy) LLM verify. Lý do chọn modular: kiểm soát offset ký tự chặt, đo/sửa từng khối, và **rẻ ngân sách 9B**.

**Ngân sách 9B TỔNG — cấu hình inference đề xuất (đã chốt)**:
| Khối | Model | Params |
|---|---|---|
| NER (A) | XLM-R-large (giữ lớn vì là nút thắt) | ~560M |
| Bi-encoder linking (B) | SapBERT (nền XLM-R-base) | ~270M |
| Reranker (B) | cross-encoder **mMiniLM ~118M** (fine-tune domain) — *không* dùng bge-v2-m3 570M (thừa cho task tên ngắn) | ~118M |
| (tùy) LLM verify/hard-case (C) | Qwen2.5-7B | ~7,600M |
| **Tổng (có LLM)** | | **~8.55B < 9B** ✅ margin ~450M |
| **Tổng (encoder-only, chưa LLM)** | | **~0.95B** ✅ dư lớn |

- Reranker cố tình dùng model nhỏ (~118M): task chỉ rerank *tên ngắn* (cụm y tế ↔ tên mã), không phải passage dài → base to không giúp; fine-tune domain quan trọng hơn size. Đo bi-encoder một mình trước, chỉ thêm reranker nếu tăng điểm.
- **Không** chạy 2 LLM 7B đồng thời. Nếu cần margin rộng hơn: hạ NER→XLM-R-base (~270M) hoặc LLM→Qwen2.5-3B.

## 5. Thứ tự thực thi khuyến nghị (mỗi bước = 1 experiment, đo trên dev gold)

1. **DATA_PLAN cấp 1** (entity replacement) → tập train NER v1. *(kiểm chứng "cơ bản đã đủ chưa")*
2. **A: NER XLM-R** thay `src/extraction` → đo delta so với 16.34. Kỳ vọng nhảy mạnh (hết mù văn xuôi).
3. **B: SapBERT retrieval** thay fuzzy candidate → đẩy 0.4.
4. **A: assertion classifier** (nếu rule chưa đủ) → đẩy 0.3.
5. **B: reranker + ICD hierarchy/RxNorm relation** → tinh candidate.
6. **C: verification agent** → đẩy trần.
7. **ensemble** (A multi-seed/model, A∪C) → chốt.

**Cần quyết trước bước 1**: chốt base NER model + phương án synthetic cấp 1 (xem câu hỏi mở).

## Câu hỏi mở / TODO cần quyết định

- [ ] Chốt base NER: XLM-R-base (đề xuất) vs PhoBERT vs ensemble. → benchmark nhanh sau khi có synthetic.
- [ ] Verify/hoàn thiện **dev gold** (13→15 file) để đo tin cậy — hiện là gold v1 assistant.
- [ ] Nguồn synthetic cấp 1: chỉ KB names, hay + dịch MIMIC/i2b2? (xem DATA_PLAN).
- [ ] SapBERT: dùng bản EN gốc trước, hay fine-tune song ngữ ngay từ `icd10_vn.csv`?
- [x] LLM sinh training data: **BẮT BUỘC self-host ≤9B, không API ngoài** (đã chốt) — vì nộp cả code sinh synthetic + file synthetic gốc, code bị BTC review. Chi tiết DATA_PLAN §PHẦN 2.
- [x] Luật thi cho dùng ICD-10/RxNorm/UMLS/sách làm KB + tạo data train (IDEAS_2 §1).
- [x] Kiến trúc: modular pipeline (chốt).

---

## Ý tưởng đã thử / đã loại bỏ

### ✅ "Abstention là lợi thế khi NER chưa sạch" — ĐÚNG, đã kiểm chứng bằng BTC (đừng rút lại lần nữa)
- **Nội dung**: NER over-predict → nhiều CHẨN_ĐOÁN/THUỐC false-positive. Trả rỗng cho chúng ăn `J(∅,∅)=1.0`; gán mã cho chúng ăn 0. → **abstain sinh điểm thật**.
- **Bằng chứng BTC (A/B sạch tuyệt đối)**: exp_0010 (sap_th 0.7, coverage 49%) vs exp_0012 (sap_th 0.5, coverage 99%) — chỉ khác matcher, BTC báo `WER 65.9308` và `J_assertion 35.9491` **giống hệt** ở cả hai → **cand 19.0448 → 13.2899 (−30%)**. Phủ mã cho span rác làm TỤT điểm.
- ⚠️ **Lịch sử**: sáng 2026-07-15 bài học này bị **rút lại NHẦM** dựa trên một bản "sửa" `src/eval/metric.py` (đổi concept thừa từ `J(∅,∅)=1` thành 0). Bản sửa đó SAI và **đã bị hoàn tác** — nó làm dev **mù hoàn toàn** trước exp_0010 vs exp_0012 (cả hai đều 0.1647). Chi tiết + bảng đối chiếu: [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) §exp_0012.
- **Bài học phương pháp**: bản "sửa" được biện minh bằng **độ khớp tuyệt đối** với BTC (0.116 vs 0.107). Đó là bẫy — metric nội bộ lệch tuyệt đối là bình thường, thứ cần là **xếp hạng đúng**. **Không bao giờ chỉnh metric theo độ khớp tuyệt đối với BTC.**

### Dense retrieval off-the-shelf cho candidate (exp_0002) — ❌ LOẠI BỎ
- Hybrid dense (`paraphrase-multilingual-MiniLM` / `e5-base`) + lexical cho ICD → candidates **tụt 0.213→0.100**.
- Nguyên nhân: embedder general chưa canh chỉnh y khoa (`hen suyễn`→"tai trong"); e5 xếp đúng top nhưng margin ~0.04 so mã rác. Hạ ngưỡng lexical cũng tệ hơn.
- **Bài học → đã đưa vào [IDEAS_2.md](IDEAS_2.md)**: phải dùng **SapBERT-style domain-adapted embedder**, không dùng general embedder. Ngưỡng lexical ICD=78 là tốt, giữ.

### KB-description reranker (exp_0028/0029, C1/C2 TRAINING_WORKFLOW_PLAN.md) — ❌ LOẠI BỎ
- Ý tưởng: cross-encoder rerank bằng mô tả KB đầy đủ (phân cấp ICD + đồng nghĩa RxNorm, 100%
  rule-based từ CSV có sẵn, không LLM) thay vì tên trần — hướng OpenBioNER cho bài toán linking.
- **Cùng span exp_0026 → dev tin trực tiếp**: candidates_score **0.3333 → 0.3011** (`max_length=64`,
  nghi ngờ do mô tả dài bị cắt cụt) → sửa `max_length=160` → **0.2903, còn TỆ hơn**. Vậy KHÔNG phải
  do truncation — mô tả dài (thêm chương/khối/đồng nghĩa) làm loãng tín hiệu relevance của
  cross-encoder **chưa fine-tune**, nó không biết cân trọng phần mô tả phụ so với tên chính.
- **Bài học**: description-conditioning chỉ có triển vọng nếu **fine-tune** cross-encoder trên cặp
  KB thật (Module C3/C5, 211,890 cặp) — dùng mô tả với reranker off-the-shelf không đủ, có thể còn
  phản tác dụng. `RerankMatcher.use_description` giữ default `False`.

### Entity masking A/B (exp_0030, A2 TRAINING_WORKFLOW_PLAN.md) — ❌ không cải thiện rõ, dừng
- Ý tưởng OpenBioNER: che TOÀN BỘ token của 1 entity (không phải từng token rời) bằng `[MASK]`
  với xác suất `p` lúc train, ép model dùng ngữ cảnh thay vì học thuộc mặt chữ.
- A/B trên `train_v5c` (p=0/0.1/0.3), so bằng `diagnose_boundary.py` (span khác NER, dev không tin
  trực tiếp): `p=0.1` cho tín hiệu **trái chiều** — `missed` 21.6%→18.5% và `candidates_score`
  0.3014→0.3302 tốt hơn (đúng giả thuyết: tổng quát hoá tốt hơn cho linking), nhưng `wrong_type`
  6.2%→8.6% và `assertions_score` 0.6612→0.5514 tệ hơn rõ, kéo `final_score` xuống (0.3941→0.3717).
  `p=0.3` tệ ở hầu hết mọi mặt.
- **Bài học**: với quy mô data hiện có (1269 doc), whole-entity masking chưa cho lợi ích ròng —
  đánh đổi giữa "tổng quát hoá linking" và "phân biệt type" chưa nghiêng về phía có lợi. Có thể
  khác trên data lớn hơn (`v4_mix` 8830 doc) nhưng chưa kịp thử (chi phí train cao hơn nhiều) —
  để ngỏ cho lần sau, không kết luận "masking luôn tệ", chỉ "chưa thấy lợi ích ở quy mô đã thử".
