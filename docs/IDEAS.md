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

---

## 1. Ta đang ở đâu (dữ kiện, không phỏng đoán)

- **Baseline Tier 0** (rule/fuzzy, 0 model): điểm THẬT từ BTC = **16.34/100** (text 19.2, assert 22.5, cand 9.6). Chi tiết `EXPERIMENTS_LOG.md`.
- **exp_0003 — Tier 1 NER (XLM-R fine-tune synthetic)** ✅ **ĐIỂM THẬT BTC = 22.18 (+5.84 vs baseline 16.34)**. text 28.63 (+9.45), assert 31.03 (+8.58), cand 10.71 (+1.08).
  - 🔑 **Bài học lớn**: dev báo text sẽ TỤT (0.328→0.207) nhưng BTC text lại TĂNG mạnh → **dev gold thiếu occurrence phạt oan recall; over-predict KHÔNG hại text trên gold đầy đủ**. → Không tin dev cho text/recall; dùng BTC làm chuẩn. Nỗi lo over-predict đã sai.
  - **candidates vẫn thấp nhất (10.71, weight 0.4)** vì còn fuzzy → **Phase 2 SapBERT là đòn bẩy lớn nhất** còn lại.
- **Đã loại bỏ**: dense retrieval off-the-shelf (exp_0002) — embedder general quá yếu (xem cuối trang).
- **Case study** (6, 8, 25, 93 rỗng ở baseline): NER Tier 1 đã bắt được khái niệm trong văn xuôi (giải nút thắt), nhưng cần tiết chế over-predict.

### 🔑 Việc quan trọng nhất tiếp theo (trước khi sang Phase 2)
1. **Giảm mật độ entity trong synthetic** (nguyên nhân over-predict): synthetic hiện vẫn dày entity hơn note thật → NER over-label. Tăng tỉ lệ O (câu/đoạn không entity), giảm entity/câu, để precision khớp phân phối thật. Rồi retrain + đo lại.
2. **Hoàn thiện dev gold** (đang INCOMPLETE — đếm sót occurrence) → text_score mới đáng tin. Nên annotate đầy đủ mọi occurrence theo convention đề (mỗi lần xuất hiện = 1 concept).
3. Đo exp_0003 trên BTC để biết text/WER thật (dev không tin được do gold thiếu).

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

### Dense retrieval off-the-shelf cho candidate (exp_0002) — ❌ LOẠI BỎ
- Hybrid dense (`paraphrase-multilingual-MiniLM` / `e5-base`) + lexical cho ICD → candidates **tụt 0.213→0.100**.
- Nguyên nhân: embedder general chưa canh chỉnh y khoa (`hen suyễn`→"tai trong"); e5 xếp đúng top nhưng margin ~0.04 so mã rác. Hạ ngưỡng lexical cũng tệ hơn.
- **Bài học → đã đưa vào [IDEAS_2.md](IDEAS_2.md)**: phải dùng **SapBERT-style domain-adapted embedder**, không dùng general embedder. Ngưỡng lexical ICD=78 là tốt, giữ.
