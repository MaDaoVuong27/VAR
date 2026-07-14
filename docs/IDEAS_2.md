# IDEAS_2 — Hướng B: RAG / Entity Linking / Knowledge Graph (khối candidate, trọng số 0.4)

> 1 trong 3 hướng. Điều hướng + so sánh: [IDEAS.md](IDEAS.md). Liên quan: [IDEAS_1.md](IDEAS_1.md) (NER cung cấp span đầu vào cho khối này), [DATA_PLAN.md](DATA_PLAN.md).

## 0. Phạm vi & vì sao quan trọng

Khối này giải bài **candidate mapping**: span khái niệm (từ NER) → mã chuẩn (`CHẨN_ĐOÁN`→ICD-10, `THUỐC`→RxNorm). Trọng số **0.4 — cao nhất**, và đang là điểm yếu nhất (0.096 thật). Đây thực chất là bài toán **Medical Entity Linking (MEL)** kinh điển, KHÔNG phải QA — điều này định hình mọi quyết định bên dưới.

## 1. Luật thi — đã xác nhận ĐƯỢC PHÉP

Đọc `TASK/de_bai.md`:
- ICD-10 + RxNorm là **CSDL chuẩn được đề chỉ định** cho candidate → chắc chắn được dùng làm knowledge base.
- Đề **khuyến khích**: *"thí sinh cần sử dụng các giải pháp nằm ngoài lời giải chính để tạo thêm dữ liệu nhằm huấn luyện mô hình"* → dùng **UMLS, SNOMED, sách/guideline y khoa** để (a) xây KB retrieval, (b) sinh dữ liệu train embedder — **hợp lệ**.
- Ràng buộc duy nhất áp vào khối này: mọi thứ chạy **offline** lúc inference (không API ngoài), model self-host tính vào ngân sách **9B tổng**. Output candidate **bắt buộc là mã ICD-10/RxNorm** (không phải SNOMED/UMLS — chúng chỉ là cầu nối trung gian).

→ Kết luận: được xây KB/graph trên ICD-10 + RxNorm (+ UMLS/sách làm phụ trợ train), miễn là index tra cứu chạy local.

## 2. Bài học đã có: off-the-shelf embedder KHÔNG dùng được (exp_0002)

Đã thử dense hybrid (MiniLM/e5-base) → candidates **tụt** 0.213→0.100. Embedder đa ngôn ngữ general cho `hen suyễn`→"tai trong", `viêm phổi`→"viêm phổi sơ sinh"; e5 xếp đúng lên top nhưng margin ~0.04 so với mã rác. **Nguyên nhân**: embedder general không được canh chỉnh (align) theo không gian khái niệm y khoa. → cần **domain-adapted embedder**.

## 3. Giải pháp SOTA: SapBERT-style bi-encoder + reranker + multistage

### 3.1 Bi-encoder canh chỉnh (SapBERT)
[SapBERT (NAACL'21)](https://arxiv.org/abs/2010.11784) — self-alignment pretraining bằng **metric learning trên UMLS**: kéo các tên gọi khác nhau của *cùng 1 khái niệm* lại gần, đẩy khái niệm khác ra xa. Đạt SOTA MEL "one-model-for-all", có **bản cross-lingual (XL-BEL)**. Đây đúng là thứ exp_0002 thiếu: một không gian vector nơi "hen suyễn" ≈ "Hen" ≈ "asthma" ≈ J45.
- **Cách dùng**: encode toàn bộ tên ICD-10 (VN+EN) + RxNorm bằng SapBERT → index (FAISS). Query = span, cosine top-k.
- **Canh chỉnh tiếng Việt**: SapBERT gốc là EN. Cần fine-tune thêm trên **cặp (tên bệnh VN ↔ tên EN/mã)** — lấy từ chính `icd10_vn.csv` (đã có song ngữ!) + RxNorm synonyms. Đây là bước domain+lingual adaptation, dùng chính KB ta có.

### 3.2 Hybrid + reranker
- **Hybrid** = lexical (RapidFuzz, đã có, mạnh cho tên thuốc EN/mã trùng ký tự) **∪** dense SapBERT (mạnh cho paraphrase VN). Bài học exp_0002: **đừng để dense đè lexical** — hợp nhất có kiểm soát (ưu tiên lexical khi khớp cao, dense bù khi lexical rỗng).
- **Cross-encoder reranker**: với top-k ứng viên, một cross-encoder (query, candidate-name) chấm lại → chọn mã cuối. Đây là nơi quyết định điểm 0.4. Reranker nhỏ (~110M), trong budget.

### 3.3 Multistage (kết hợp LLM cho ca khó)
Theo [SOTA 2025 — Multilingual Clinical Entity Linking to ICD-10](https://arxiv.org/html/2509.04868v1): (1) **dictionary match** cho term rõ ràng (nhanh, chính xác); (2) **in-context LLM** cho term mơ hồ còn lại. Ta áp dụng: dict/lexical bắt ca dễ, SapBERT+reranker cho phần giữa, LLM self-host (hướng C) chỉ để chuẩn hoá tên/chọn mã cho ca cực khó — **LLM đề xuất TÊN chuẩn rồi tra KB, không tự bịa mã** (chống hallucination mã ICD).

## 4. Knowledge Graph — phản biện: cần tới đâu?

User đề cập DA-RAG/HyRAG/graph-RAG (retrieve từ chunk + topology/graph + semantic layer). **Cần tỉnh táo**: các kiến trúc graph-RAG đó thiết kế cho **multi-hop QA reasoning** (câu hỏi cần nối nhiều facts). Bài toán của ta là **entity linking 1-hop** (term → mã) — phần lớn KHÔNG cần multi-hop. Xây full graph-RAG dễ **overkill** và tốn công mà không đẩy được điểm.

**Giá trị THẬT của cấu trúc graph ở đây** là **ontology hierarchy**, không phải reasoning:
- **ICD-10 = cây phân cấp** (chương → khối → mã 3 ký tự → mã 4-5 ký tự). Hữu ích để: (a) chọn **đúng granularity** (baseline hay map "viêm phổi" chung vào mã chuyên biệt — dùng cây để lùi về mã cha J18 tổng quát khi query mơ hồ); (b) lọc theo **cờ cột 24-29** (không dùng làm bệnh chính / có mã con cụ thể hơn) đã có sẵn trong `icd10_vn.csv`; (c) tính điểm 1 phần khi trượt mã con nhưng đúng nhánh.
- **RxNorm = đồ thị quan hệ** (ingredient IN → SCD → SBD → brand, qua `RXNREL`). Hữu ích để: từ tên hoạt chất suy ra clinical drug đúng liều, hoặc ngược lại chuẩn hoá brand→ingredient. Đây giải đúng lỗi "granularity thuốc" của baseline.
- **Sách/guideline y khoa** (nếu dùng): là văn bản **phi cấu trúc** → muốn thành graph phải tự chunk + extract entity + relation (tốn công, nhiễu). Đặc điểm: giàu quan hệ ngữ nghĩa (triệu chứng→bệnh→thuốc) nhưng **không trực tiếp cho ra mã ICD/RxNorm**. → chỉ đáng dùng để **mở rộng đồng nghĩa / sinh synonym cho SapBERT**, KHÔNG nên là graph truy vấn lúc inference.

**Khuyến nghị**: KHÔNG xây graph-RAG phức tạp. Dùng: (1) **SapBERT retrieval** làm lõi; (2) **ICD-10 hierarchy + RxNorm relation như ràng buộc/re-rank** (đồ thị nhẹ từ chính KB, không cần graph DB); (3) sách/guideline chỉ để làm giàu synonym khi sinh data. Đây là "graph vừa đủ", đúng bản chất 1-hop của bài.

## 5. Đặc điểm KB nếu build graph (trả lời câu hỏi user)

| Nguồn | Cấu trúc graph | Dùng làm gì | Chi phí |
|---|---|---|---|
| ICD-10 (Bộ Y tế) | Cây phân cấp mã, có song ngữ + cờ | Chọn granularity, ràng buộc candidate bệnh | Thấp (đã có CSV) |
| RxNorm | Đồ thị IN↔SCD↔SBD↔brand (RXNREL) | Chuẩn hoá granularity thuốc | TB (parse RXNREL) |
| UMLS | Đồ thị 4M concept + synonym đa ngôn ngữ | Train/align SapBERT, mở rộng synonym | Cao (nặng, cần license) |
| Sách/guideline VN | Phi cấu trúc → phải tự build | Sinh synonym, KHÔNG cho ra mã | Cao, nhiễu |

## 6. Thứ tự thực thi

1. **Build FAISS index** ICD-10 (VN+EN) + RxNorm bằng SapBERT gốc → thay fuzzy trong `src/normalization` → đo (kỳ vọng > exp_0002 vì SapBERT canh chỉnh y khoa).
2. **Fine-tune SapBERT** trên cặp song ngữ từ KB → đo delta.
3. **+ reranker cross-encoder** → chốt candidate.
4. **+ ICD hierarchy / RxNorm relation** như hậu xử lý chọn granularity.
5. (tùy) multistage LLM cho ca khó.

## Nguồn tham khảo
- [SapBERT: Self-Alignment Pretraining for Biomedical Entity Representations](https://arxiv.org/abs/2010.11784) + [code](https://github.com/cambridgeltl/sapbert)
- [Multilingual Clinical Entity Linking to ICD-10 (2025)](https://arxiv.org/html/2509.04868v1)
- [Multistage biomedical concept normalization w/ LLMs (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12527512/), [CDE-Mapper: RAG for clinical data element linking](https://arxiv.org/pdf/2505.04365)
