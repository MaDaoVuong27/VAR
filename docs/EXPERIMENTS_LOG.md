# Tổng hợp kết quả thử nghiệm

Bảng roll-up của mọi experiment trong `experiments/`. Mỗi dòng ứng với 1 folder `experiments/exp_XXXX_<tên>/`. Chi tiết cấu hình từng experiment nằm trong `config.yaml` của folder đó; chi tiết ý tưởng đứng sau nằm trong [IDEAS.md](IDEAS.md).

Công thức nhắc lại: `final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score`

## 📦 BTC nâng cấp đề (2026-07-16) — input KHÔNG đổi, nghi ground truth private đổi

BTC báo "nâng cấp đề thi", cấp zip `data/raw_new/input.zip`. Đã kiểm tra: **100/100 file `.txt` giống hệt byte-for-byte** `data/raw/input/` cũ (checksum tổng thư mục trùng khớp, cùng 132.336 ký tự, cùng median 1229). → **input công khai không đổi**; nếu có nâng cấp thật, nó nằm ở ground truth private mà BTC dùng để chấm, không quan sát được từ phía ta.

**Quyết định**: từ nay `data/raw_new/` là nguồn test chuẩn (đã cập nhật default path trong `scripts/run_pipeline_exp.py`, `src/pipeline.py`, `CLAUDE.md`, `README.md`). `data/raw/` cũ giữ lại để đối chiếu lịch sử, không xoá. Vì nội dung giống hệt, **mọi experiment đã chạy trước đó (exp_0001..0012) vẫn nguyên giá trị** — không cần chạy lại pipeline, chỉ cần nộp lại `output.zip` đã có nếu muốn đo lại trên ground truth mới.

**Kết quả nộp lại exp_0010 sau "nâng cấp"**: `WER 65.9308 · J_assertion 35.9491 · J_candidates 19.0448 · final 28.62340` — **trùng khít tới từng chữ số thập phân** với lần nộp gốc 2026-07-15. Không phải final_score tình cờ giống (có thể do làm tròn) mà cả 3 raw metric đều y hệt → bằng chứng cứng rằng **cách chấm cho bài nộp cụ thể này không đổi**.

**Kết luận**: "nâng cấp đề thi" không ảnh hưởng gì quan sát được từ phía ta ở cả 2 lớp (input công khai giống hệt, chấm điểm cho submission đã có giống hệt). Có thể: (a) nâng cấp là cho vòng/phần khác (vd private test vòng sau) chưa áp dụng ở đây; (b) nâng cấp không đụng tới phần liên quan tới ta; (c) thông báo nâng cấp không kèm thay đổi thực chất tới lúc này. → Tiếp tục làm việc bình thường trên `data/raw_new/`, không cần điều chỉnh gì thêm. Nếu BTC gửi thêm tài liệu/thông báo cụ thể về nâng cấp, đọc lại `TASK/` xem có cập nhật không.

## 🔓 Giải mã bảng chỉ số BTC (2026-07-15) — đọc ngược ra cả 3 thành phần

Trang nộp bài của BTC hiển thị: `WER`, `J_assertion`, `J_candidates`, `num_scored`, `num_records`. Đối chiếu với exp_0007 cho thấy:

```
text_score   = 100 − WER          ← BTC báo WER TRỰC TIẾP, không phải text_score
assert_score = J_assertion
cand_score   = J_candidates
final = 0.3·(100−WER) + 0.3·J_assertion + 0.4·J_candidates
```

Kiểm chứng trên exp_0007: `0.3×(100−72.2255) + 0.3×30.1416 + 0.4×16.1736 = 23.84427` vs BTC báo **23.84430** (lệch 0.00003 = làm tròn ở các chỉ số hiển thị). ✅

→ **Mỗi lượt nộp giờ cho 3 phép đo, không phải 1.** Ghi lại **nguyên văn mọi chữ số thập phân** của BTC, không làm tròn.

> ⚠️ **Điểm dev đã được CHẤM LẠI (2026-07-15) sau khi sửa lỗi metric** — xem [§Lỗi metric](#-lỗi-metric-đã-sửa-2026-07-15-đọc-trước-khi-so-điểm-dev-cũ) cuối trang. Mọi điểm dev trong bảng này là **bản sau sửa** (`python scripts/rescore_all.py`); điểm dev CŨ đã ghi trước 2026-07-15 **thổi phồng 2–3.5×** và không dùng lại được.
>
> Điểm dev chấm trên **gold v1** (`data/labeled/ground_truth`, 15 file, assistant-annotated, **INCOMPLETE** — đếm sót occurrence, candidate best-effort). `text_score` = proxy soft-F1 (không phải WER literal). Dùng **so sánh tương đối trong cùng họ cấu hình**; điểm tuyệt đối lấy từ **submission BTC**.

| ID | Ngày | Mô tả ngắn | text | assert | cand | final | Nhận xét |
|---|---|---|---|---|---|---|---|
| [exp_0001_baseline](../experiments/exp_0001_baseline/) | 2026-07-11 | Tier 0: rule/dict NER + assertion rule + fuzzy candidate (0 model) | 0.328 | 0.285 | 0.143 | 0.241 | dev 15-file gold (đã chấm lại). |
| **exp_0001 — ĐIỂM THẬT BTC** | 2026-07-12 | Baseline, hệ thống BTC (100 file) | **0.192** | **0.225** | **0.096** | **0.163** | ⭐ Mốc thật 16.34/100. NER mù văn xuôi = nút thắt. |
| [exp_0002_tier1_hybrid](../experiments/exp_0002_tier1_hybrid/) | 2026-07-11 | dense MiniLM + lexical cho ICD candidate | — | — | — | — | ❌ LOẠI (embedder general yếu). ⚠️ Folder **không có `predictions/`** → không chấm lại được; điểm dev cũ (0.378/0.622/0.100/0.340) theo metric lỗi, **không so được** với các dòng khác. |
| [exp_0003_ner_xlmr](../experiments/exp_0003_ner_xlmr/) | 2026-07-14 | Tier 1: NER XLM-R fine-tune synthetic + rule assertion + fuzzy candidate; min_conf=0.95 | 0.207 | 0.209 | 0.116 | 0.171 | dev sau sửa. cand 0.116 **khớp sát BTC 0.107** (lệch 0.009). |
| **exp_0003 — ĐIỂM THẬT BTC** | 2026-07-14 | NER Tier 1 (min_conf=0.95), BTC 100 file | **0.286** | **0.310** | **0.107** | **0.222** | ⭐ **+5.84 vs baseline (16.34→22.18)** — **BEST THẬT**. text +9.45, assert +8.58, cand +1.08. |
| [exp_0003b_ner_conf06](../experiments/exp_0003b_ner_conf06/) | 2026-07-14 | NER min_conf=**0.6** (recall cao hơn) | 0.145 | 0.146 | 0.081 | 0.120 | dev sau sửa — xếp hạng ĐÚNG so với exp_0003 (BTC cũng nói 0.095 < 0.107). |
| **exp_0003b — ĐIỂM THẬT BTC** | 2026-07-14 | NER min_conf=0.6, BTC | 0.261 | 0.290 | 0.095 | 0.203 | ❌ **20.29 < 22.18** — ngưỡng thấp tệ hơn CẢ 3 thành phần. → **precision > recall**, chốt **min_conf=0.95**. |
| [exp_0004_ner_sapbert](../experiments/exp_0004_ner_sapbert/) | 2026-07-14 | NER + **SapBERT** candidate (k=1, th=0.5, luôn trả mã) | 0.207 | 0.209 | 0.133 | 0.178 | dev sau sửa: **0.133 > fuzzy 0.116** → SapBERT gán mã đúng hơn fuzzy trên concept CÓ THẬT. |
| [exp_0005_ner_hybrid](../experiments/exp_0005_ner_hybrid/) | 2026-07-14 | NER + hybrid (fuzzy trước, SapBERT lấp khi rỗng, sap_th=0.5) | 0.207 | 0.209 | 0.116 | 0.171 | dev sau sửa **trùng khít exp_0003** → trên gold hiện tại fuzzy luôn trả mã, SapBERT không bao giờ được gọi lấp. Khác biệt BTC (0.078 vs 0.107) nằm ở concept mà dev gold KHÔNG có → dev mù. |
| **exp_0005 — ĐIỂM THẬT BTC** | 2026-07-14 | NER + hybrid, BTC | 0.286 | 0.310 | **0.078** | **0.210** | ❌ **21.01 < 22.18** — candidates TỤT (10.71→7.77). text/assert y hệt exp_0003. |

| [exp_0006_hybrid_th07](../experiments/exp_0006_hybrid_th07/) | 2026-07-14 | NER + hybrid, SapBERT abstain th=0.7 (chỉ *lấp* chỗ fuzzy rỗng) | 0.207 | 0.209 | 0.116 | 0.171 | dev sau sửa — cũng trùng khít exp_0003 (xem exp_0005). |
| **exp_0006 — ĐIỂM THẬT BTC** | 2026-07-14 | NER + hybrid abstain, BTC | 0.286 | 0.310 | 0.104 | **0.221** | ~ngang 22.18 (cand 10.42 < fuzzy 10.71). Hybrid *giữ mã sai của fuzzy* cho concept thật → không cứu được. |
| [exp_0007_sapbert_th07](../experiments/exp_0007_sapbert_th07/) | 2026-07-14 | **NER + SapBERT-only abstain th=0.7 (THAY fuzzy) + tách span xuống dòng** | 0.204 | 0.216 | **0.147** | **0.185** | dev cand cao nhất sau sửa (vs fuzzy/hybrid 0.116, SapBERT-no-abstain 0.133). |
| **⭐ exp_0007 — ĐIỂM THẬT BTC** | 2026-07-15 | NER v2 + SapBERT-only abstain th=0.7, BTC 100 file | **27.7745** | **30.1416** | **16.1736** | **23.84430** | 🏆 **BEST THẬT (+1.66 vs exp_0003 22.18)**. Nguyên văn BTC: `WER 72.2255 · J_assertion 30.1416 · J_candidates 16.1736 · num_scored 100 · num_records 100`. **cand 10.71→16.1736 (+51%)** → SapBERT thắng fuzzy DỨT KHOÁT. text −0.86, assert −0.89 (thủ phạm: `split_newlines`, thay đổi duy nhất còn lại). |
| [exp_0008_sapbert_icdk2](../experiments/exp_0008_sapbert_icdk2/) | 2026-07-15 | exp_0007 + **ICD k=2** — dò convention gold BTC | 0.204 | 0.216 | 0.116 | 0.173 | dev TỤT (0.147→0.116). |
| **exp_0008 — ĐIỂM THẬT BTC** | 2026-07-15 | exp_0007 + ICD k=2, BTC | **27.7745** | **30.1416** | **14.1952** | **23.05290** | ❌ **< 23.84430**. Nguyên văn: `WER 72.2255 · J_assertion 30.1416 · J_candidates 14.1952`. 🔑 **WER + J_assertion GIỐNG HỆT exp_0007 tới từng chữ số** (k=2 chỉ đụng candidates) → đối chứng sạch tuyệt đối + xác nhận công thức lần 2. **KẾT LUẬN: gold BTC chủ yếu 1 mã/concept** — ví dụ K21.0+K21.9 trong đề là ngoại lệ. → **chốt k=1, KHÔNG đầu tư dự đoán đa mã.** |
| [exp_0009_v2_nosplit](../experiments/exp_0009_v2_nosplit/) | 2026-07-15 | exp_0007 nhưng **TẮT `split_newlines`** | 0.207 | 0.209 | 0.133 | 0.178 | Đối chứng sạch vs exp_0007 (chỉ khác split). BTC text/assert sẽ = exp_0003 (28.63/31.03) → **điểm hoà ở BTC cand 14.87**. ⚠️ Bác bỏ giả định cũ "cand không phụ thuộc split": tách span đổi chuỗi đưa vào SapBERT → đổi mã. ⏳ chờ BTC. |
| [exp_0010_v3large_split](../experiments/exp_0010_v3large_split/) | 2026-07-15 | **NER XLM-R-large (560M) trên synthetic v3** + SapBERT th=0.7 k=1 | 0.218 | 0.228 | 0.165 | 0.200 | BEST dev — thắng exp_0007 trên CẢ 3 (text +6.5%, assert +5.5%, cand +11.7%). Cơ chế: `CHẨN_ĐOÁN` 940→794 (−16%), tổng span 2553→2490, tỉ lệ gán được mã 45%→49%. |
| **🏆 exp_0010 — ĐIỂM THẬT BTC** | 2026-07-15 | NER v3-large + SapBERT th=0.7, BTC 100 file | **34.0692** | **35.9491** | **19.0448** | **28.62340** | 🏆 **BEST THẬT (+4.78 vs exp_0007 23.84)** — bước nhảy lớn nhất từ trước tới nay. Nguyên văn: `WER 65.9308 · J_assertion 35.9491 · J_candidates 19.0448`. CẢ 3 tăng mạnh: text +6.29 (+23%), assert +5.81 (+19%), cand +2.87 (+18%). Xác nhận công thức lần 3 (28.62341 vs 28.62340). ✅ **dev (sau sửa metric) dự báo ĐÚNG thứ hạng cả 3 thành phần — kiểm chứng ngoài mẫu lần 2**; dev báo +6% còn BTC +23% → dev là chỉ báo hướng đúng nhưng **bảo thủ**. ⚠️ Gộp 2 thay đổi (XLM-R-large + synthetic v3, gồm cả fix sliding-window cứu 45.7% nhãn) → không tách được đóng góp. |
| **[exp_0012_v3large_th05](../experiments/exp_0012_v3large_th05/)** | 2026-07-15 | exp_0010 + **sap_th 0.7→0.5** (coverage 49%→99%) | 0.218 | 0.228 | 0.165 | 0.200 | ⚗️ **PHÉP THỬ QUYẾT ĐỊNH — dev MÙ HOÀN TOÀN** (giống exp_0010 tới từng chữ số) vì: concept thật trong gold đều có sim>0.75 (ngưỡng không đụng tới), còn concept thừa ăn 0 điểm dù có mã hay không. span/type/assertions **y hệt exp_0010** → BTC sẽ báo WER & J_assertion y hệt → **mọi thay đổi CHỈ từ J_candidates**. ⏳ chờ BTC. |
| [exp_0013_v4mix_split](../experiments/exp_0013_v4mix_split/) | 2026-07-16 | **NER XLM-R-large trên synthetic v4** (template 6k + Qwen-prose 2830, `data/synthetic/train_mix.jsonl`) + SapBERT th=0.7 | 0.246 | 0.661 | 0.366 | 0.418 | dev: text so trực tiếp được (0.218→0.246 ↑); cand dev tụt nhưng **numerator-decomp dự báo cand THẬT tăng** — BTC xác nhận. |
| **🏆 exp_0013 — ĐIỂM THẬT BTC** | 2026-07-16 | NER v4-mix + SapBERT th=0.7, BTC 100 file | **38.6905** | **36.3798** | **23.1624** | **31.78610** | 🏆 **BEST THẬT (+3.16 vs exp_0010 28.62)**. Nguyên văn: `WER 61.3095 · J_assertion 36.3798 · J_candidates 23.1624`. **Prose synthetic (Qwen self-host) đẩy CẢ 3**: text +4.62 (prose dạy NER bắt khái niệm trong văn xuôi), cand +4.12, assert +0.43. Công thức khớp lần 4 (31.78605 vs 31.78610). ✅ **numerator-decomp CỨU 1 quyết định thật**: dev cand tụt 0.49→0.37 nhưng bóc tách báo cand thật TĂNG (khớp gold 38→45, độ chính xác 0.33→0.36) → BTC xác nhận cand +4.12. Nếu tin dev tổng đã vứt best submission. ⚠️ 2 biến gộp: +prose VÀ −template (12k→6k) → chưa tách được cái nào gánh chính. |

| [exp_0014_prose_only](../experiments/exp_0014_prose_only/) | 2026-07-16 | **Ablation: NER XLM-R-large trên CHỈ 2830 prose** (không template) | 0.219 | 0.461 | **0.054** | 0.226 | ❌ **KẾT QUẢ ÂM RÕ — prose KHÔNG thay được template.** Sụp đúng 2 type mang candidate: CHẨN_ĐOÁN 375→42, THUỐC 165→26; **KẾT_QUẢ_XÉT_NGHIỆM = 0** (prose có 0% type này). Lý do: test 99% bán cấu trúc (mục/bullet/bảng lab), prose-only chưa từng thấy. → **prose bổ trợ template, không thay thế.** |
| **exp_0014 — ĐIỂM THẬT BTC** | 2026-07-16 | prose-only, BTC 100 file | **19.5378** | **16.576** | **4.6884** | **12.70950** | ❌ **thấp nhất trong mọi bản NER** (< cả baseline 16.34). Nguyên văn: `WER 80.4622 · J_assertion 16.576 · J_candidates 4.6884`. cand 4.69 (sụp đúng như dev báo 0.054). Công thức khớp lần 5. ✅ **dev decomp dự báo đúng lần nữa** cho một thay đổi NER-model: dev cand 0.054 → BTC 4.69 (đều "sụp"). |

### ✅ exp_0014 (prose-only) trả lời câu hỏi "prose có hơn template không": KHÔNG — chúng bổ trợ nhau

Dự đoán trước khi chạy (đã ghi): prose-only sẽ tệ vì (a) prose có **0% KẾT_QUẢ_XÉT_NGHIỆM** (hàm `_plan` không sinh), (b) không có cấu trúc mục/bullet/bảng lab mà 99/100 test có. Kết quả xác nhận cả hai:

| type (span/100 file test) | exp_0013 v4-mix | exp_0014 prose-only |
|---|---|---|
| CHẨN_ĐOÁN | 375 | **42** (−89%) |
| THUỐC | 165 | **26** (−84%) |
| KẾT_QUẢ_XÉT_NGHIỆM | 110 | **0** |

→ **Template cung cấp coverage cấu trúc (drug list, lab table); prose cung cấp coverage văn xuôi.** Mix (exp_0013 31.79) > template thuần (exp_0010 28.62) > prose thuần (dev 0.226). Không loại trừ nhau.

| [exp_0015_dense_14830](../experiments/exp_0015_dense_14830/) | 2026-07-16 | **NER XLM-R-large trên dense 14830** (12k template + 2830 prose) + SapBERT th=0.7 | **0.258** | 0.660 | 0.386 | 0.430 | dev text > exp_0013 (0.246→0.258, so trực tiếp được); cand ~hoà (khớp gold 43 vs 45, độ chính xác 0.378 vs 0.362). ⏳ chờ BTC nếu nộp. |

| [exp_0016_sapbert_ft](../experiments/exp_0016_sapbert_ft/) | 2026-07-16 | NER v4-mix (cố định) + **SapBERT fine-tune song ngữ** (in-batch InfoNCE, 58k cặp KB) th=0.7 | 0.246 | 0.661 | **0.328** | 0.403 | ❌ **FINE-TUNE NAIVE LÀM TỆ HƠN** (cand 0.366→0.328). **Span cố định (cùng NER) → dev cand TIN ĐƯỢC** → kết luận chắc, KHÔNG nộp. |

### ⚠️ exp_0016: fine-tune SapBERT bằng in-batch negative NGẪU NHIÊN thất bại — cần HARD NEGATIVE

Đo được: batch-acc → **1.000** ngay từ đầu → bài "phân biệt synonym với 63 tên KB ngẫu nhiên" **quá dễ** (SapBERT vốn giỏi). Không dạy được thứ nó THẬT SỰ yếu: chọn mã nào giữa các mã **gần giống**. Fine-tune đổi **146/375 (39%) mã CHẨN_ĐOÁN** — con dao 2 lưỡi:
- ✅ sửa đúng: `viêm họng do liên cầu` A54.5(lậu cầu)→**J02.0(liên cầu)**; `Suy tim…` F20.2(TTPL)→∅
- ❌ phá hỏng: `Lo ngại về đào thải` ∅→F40.0(sợ khoảng trống); `Suy thận` N20.0(sỏi)→Q61.4(loạn sản)

→ net âm nhẹ. **Hướng đúng nhưng thiếu tín hiệu.** Việc tiếp: (a) **hard-negative mining** (với mỗi tên, lấy láng giềng gần NHƯNG khác mã làm negative) → dạy đúng ranh giới; hoặc (b) **reranker cross-encoder** (chấm lại top-k, cơ chế phân biệt sạch hơn, không đụng không gian retrieval). Cả 2 là bước tiếp của khối candidate.

✅ **Giá trị phương pháp**: quy luật "span cố định → dev cand tin được" vừa CỨU 1 lượt nộp — nếu nộp đại exp_0016 sẽ tụt điểm. Fine-tune NER giữ nguyên, chỉ đổi matcher → so trực tiếp trên dev hợp lệ.

### exp_0017: hard-negative mining KHÔNG cứu được — còn tệ hơn cả bản naive

Thử fix trực tiếp chẩn đoán ở trên: mine 3 hard-negative/anchor bằng FAISS trên chính SapBERT gốc, train contrastive loss ép model phân biệt láng giềng gần. batch-acc giảm đúng như kỳ vọng (1.000→0.5-0.88, xác nhận task đã khó hơn, không còn trivial).

| | exp_0013 (gốc) | exp_0016 (naive) | exp_0017 (hard-neg) |
|---|---|---|---|
| dev cand | 0.3656 | 0.328 | **0.2581** ← tệ nhất |
| độ chính xác trên concept khớp gold thật | 0.3622 | — | **0.2992** ↓ |
| concept rác bị gán mã (chắc chắn 0đ) | 37/59 | — | **49/59** ↑ |
| abstain rate | 22% | 25% | **8%** ↓↓ |

**Cơ chế**: contrastive loss kéo positive pairs sát nhau → đẩy TOÀN PHỔ similarity dịch lên (kể cả match sai) → `sap_th=0.7` (hiệu chỉnh cho SapBERT gốc) mất ý nghĩa trên không gian embedding đã dịch chuyển → model "tự tin" nhầm vào cả rác lẫn concept thật bị đổi sai. Test đều thất bại: naive (âm nhẹ, in-batch quá dễ) VÀ hard-neg (âm nặng hơn, task khó nhưng threshold không theo kịp không gian mới). **Không nộp cả hai.**

→ **Dừng hướng fine-tune contrastive SapBERT ở quy mô/cách làm hiện tại.** Nếu thử lại: (a) phải **re-calibrate threshold riêng** cho mỗi checkpoint fine-tune (không dùng chung 0.7), (b) kiểm tra hard-negative mining không lẫn false-negative (2 tên "gần nhau về ký tự" có thể là SAME concept khác cách viết, không phải khác concept).

### exp_0018: sanity-check rerank OFF-THE-SHELF (không train) — cũng âm, nhưng có tín hiệu hỗn hợp

Trước khi đầu tư train reranker riêng (mMiniLM, ~30-45 phút), test nhanh (~1 phút chạy) bằng `BAAI/bge-reranker-v2-m3` có sẵn trong cache, KHÔNG fine-tune: SapBERT retrieval top-10 (giữ nguyên th=0.7, KHÔNG đụng abstain) → cross-encoder chấm lại → chọn top-1 mới.

| | exp_0013 (SapBERT top-1 trực tiếp) | exp_0018 (+ rerank off-the-shelf) |
|---|---|---|
| dev cand | 0.3656 | **0.3333** ↓ |
| abstain rate | 22% | 22% — **giữ nguyên** (đúng thiết kế, rerank không đụng ngưỡng) |

90/375 CHẨN_ĐOÁN đổi mã sau rerank — **hỗn hợp, không chỉ toàn xấu**:
- ✅ sửa đúng: `viêm họng do liên cầu` A54.5(lậu cầu)→**J02.0(liên cầu)**; `Suy thận` N20.0(sỏi)→**N17(suy thận cấp)**
- ❌ phá hỏng: `Cơn nhịp nhanh` I47(đúng)→R00.0(mã triệu chứng chung, kém đặc hiệu); `Khởi phát chuyển dạ` O62.0(gần đúng)→B08.2(ban đào, không liên quan)

**Kết luận ban đầu (theo dev, TRƯỚC khi nộp)**: có vẻ tệ hơn (0.366→0.333). Sau khi nộp, BTC nói NGƯỢC LẠI.

| **exp_0018 — ĐIỂM THẬT BTC** | 2026-07-16 | NER v4-mix + SapBERT-retrieval + rerank off-the-shelf, BTC 100 file | **38.6905** | **36.3798** | **23.4669** | **31.90790** | 🏆 **BEST MỚI (+0.12 vs exp_0013)**. Nguyên văn: `WER 61.3095 · J_assertion 36.3798 · J_candidates 23.4669`. WER/J_assertion **giống hệt exp_0013 tới từng chữ số** (xác nhận cùng span — rerank không đụng NER). J_candidates tăng nhẹ +0.3045 (+1.3%) — **NGƯỢC HƯỚNG dev báo** (dev: 0.366→0.333, tụt). Công thức khớp lần 6. |

### exp_0020: hybrid BM25 ∪ dense (RRF) + rerank — thiết kế an toàn, điểm chờ BTC

Nâng retrieval thành hybrid: pool ứng viên cho reranker = dense(SapBERT top-10) ∪ BM25(lexical top-10), hợp nhất bằng **RRF** (rank-based, tránh lỗi lệch thang điểm đã giết exp_0002). Code `src/normalization/reranker.py` class `HybridRerankMatcher`, cờ `--hybrid-rerank`.

✅ **Abstain gate GIỮ NGUYÊN** (verify: exp_0015/0019/0020 đều abstain 125/538 = 23%). Dense quyết định abstain; BM25 chỉ làm giàu pool khi KHÔNG abstain → không lặp lại lỗi exp_0002/0012.

✅ **BM25 sửa đúng lỗi flagship**: `Suy tim dãn tâm thu` F20.2 (tâm thần phân liệt!) → **I50 (suy tim) ✓** — match từ vựng "suy tim" mà dense embedding xếp thấp, reranker xác nhận. Đúng cơ chế thiết kế.

⚠️ **Chất lượng hỗn hợp** (BM25 đổi 63/538 mã): sửa vài ca (suy tim), phá vài ca (`Suy thận mạn giai đoạn V` N18.5 đúng → I12 mất giai đoạn).

| (cùng NER v6_dense, abstain 23% cả 3) | dev cand |
|---|---|
| exp_0015 SapBERT top-1 | 0.3862 |
| exp_0019 rerank | 0.3545 |
| exp_0020 hybrid BM25∪dense + rerank | 0.3439 |

⚠️ **Dev KHÔNG phân xử được ca này** — rơi đúng vùng dev không tin cậy (§exp_0018): abstain rate không đổi giữa 3 bản → dev bi quan hệ thống với rerank/hybrid. Bằng chứng: dev nói rerank(0.354) < SapBERT(0.386), nhưng BTC nói NGƯỢC (exp_0018 31.91 > exp_0013 31.79). → **hybrid vs rerank là coin-flip, chỉ BTC biết.**

| [exp_0021_v4mix_hybrid_rerank](../experiments/exp_0021_v4mix_hybrid_rerank/) | 2026-07-17 | **NER v4-mix (BEST base) + hybrid BM25∪dense + rerank** | 0.246 | 0.660 | 0.333 | 0.405 | Hybrid build lại trên nền v4-mix ĐÚNG. |
| **exp_0021 — ĐIỂM THẬT BTC** | 2026-07-17 | v4-mix + hybrid BM25∪dense + rerank, BTC | **38.6905** | **36.3798** | **23.1327** | **31.77420** | ❌ **< exp_0018 (rerank thường) 31.90790**. WER & J_assertion GIỐNG HỆT exp_0018 (chỉ đổi matcher). **J_candidates TỤT 23.47→23.13 (−0.33)** → **BM25 thêm NHIỄU nhiều hơn tín hiệu**. Cú sửa `suy tim→I50` không bù nổi các mã "hợp lý mà sai" BM25 chèn vào (N18.5→I12...). Công thức khớp lần 8. |

### 🔬 exp_0021 vs exp_0018: dev MÙ HOÀN TOÀN (không chỉ bi quan)

Cùng NER v4-mix, chỉ khác matcher (rerank vs hybrid). Đo trên dev:

| | abstain rate | độ chính xác cand TRÊN concept khớp gold |
|---|---|---|
| exp_0018 (rerank) | 22% | **0.3150** |
| exp_0021 (hybrid) | 22% | **0.3150** (giống HỆT) |

→ Hybrid và rerank cho kết quả **y hệt trên MỌI concept mà dev gold có nhãn**. Toàn bộ khác biệt BM25 nằm ở concept gold BỎ SÓT (dev không thấy). Dev không "bi quan" mà **mù tuyệt đối** cho ca này. Bằng chứng duy nhất: định tính — BM25 sửa `suy tim` F20.2→I50 (thắng lớn) nhưng phá `Suy thận mạn gđ V` N18.5→I12 (mất giai đoạn). Net chỉ BTC biết. **Ứng viên nộp thuần tuý, không có tín hiệu dev để đoán trước.**

### ❌ exp_0022: assertion CLASSIFIER thua RULE trên dữ liệu thật (overfit synthetic)

Thay rule assertion bằng XLM-R-base classifier đa nhãn (span đánh dấu [ENT], cửa sổ ngữ cảnh, 3 sigmoid). Train 80k template + 14k prose. `src/assertion/classifier.py` + `scripts/train_assertion.py`, cờ `--assertion-clf`.

**Val synthetic đẹp nhưng dev thật thua rule** (bóc tách trên concept KHỚP gold, cùng span v4-mix):

| | val synthetic isHistorical | dev thật J (matched) | dev isHistorical đúng |
|---|---|---|---|
| RULE | — | **0.7373** | **80%** |
| CLASSIFIER | 0.979 | 0.6780 ↓ | 76% ↓ |

**Nguyên nhân**: classifier học thuộc cue tiền sử SẠCH/ĐƠN GIẢN của template (`Thuốc trước khi nhập viện`, section=history) nhưng không khái quát sang cách diễn đạt tiền sử ĐA DẠNG của bệnh án thật. Rule (viết tay từ quan sát dữ liệu thật) tổng quát tốt hơn. **Val F1 synthetic 0.979 lại VÔ NGHĨA** (lần 3 xác nhận) — cùng phân phối train.

**→ Giữ RULE. Không nộp.** Assertion classifier qua synthetic hiện tại là ngõ cụt: cần (a) synthetic có ĐỘ ĐA DẠNG cue tiền sử của dữ liệu thật, hoặc (b) **dữ liệu assertion thật có nhãn = dev gold hoàn thiện**. → củng cố thêm: hoàn thiện dev gold là nút thắt gốc.

💡 Hướng rẻ hơn CHƯA thử: cải thiện chính RULE cho isHistorical (mở rộng cue, section-detection tốt hơn) thay vì thay bằng model — rule đã 80%, chỉ cần vá chỗ yếu.

### ✅ exp_0023: vá RULE isHistorical (2 bug đo được trên dev) — assert TĂNG THẬT

Chẩn đoán trực tiếp bằng `_section_map`/`_top_at` thật (không phải dataclass default sai như lần đầu) trên toàn bộ dev, tìm đúng 2 bug:

1. **`_match_header` lây nhiễm section-state** ([extractor.py](../src/extraction/extractor.py)): câu văn xuôi "Tiền sử **2 ngày** đau bụng ngày càng nặng" (diễn biến, nằm trong section "present") bị hiểu nhầm là header "Tiền sử bệnh" vì `_match_header` dùng `.search()` không phân biệt header thật với câu chứa từ "tiền sử". Đặt lại `top="history"` sai, lây sang MỌI dòng sau đó (file 66: 5 triệu chứng hiện tại bị gán isHistorical sai). Fix: thêm `(?!\s*\d)` loại trừ "tiền sử N ngày/tháng".
2. **`_HIST_CUE` quét cả dòng** ([rules.py](../src/assertion/rules.py)): dòng văn xuôi dài không xuống dòng (file 50, >150 ký tự) khiến cue "trước nhập viện" cách concept **159 ký tự** vẫn tính là cùng ngữ cảnh. Fix: thu hẹp về cửa sổ cục bộ 100 ký tự trước / 40 sau quanh span (giống cách `_has_negation` đã làm từ đầu — bất nhất trong code cũ).

**Kết quả trên toàn bộ dev (118 concept, exact-match toàn assertion)**:

| | trước vá | sau vá |
|---|---|---|
| exact-match | 86.4% | **92.4%** |
| isNegated / isFamily | 97% / 97% | 97% / 97% (không đổi — đúng ý đồ, không phá cái đang tốt) |
| **isHistorical** | 90% | **97%** |

Còn lại: 1 false-positive (file 50, cue khác vẫn lọt cửa sổ) + 3 miss (file 66, ca sub-header "Các sự kiện trước khi nhập viện" — cố ý KHÔNG vá, rủi ro overfit 1 file cao hơn lợi ích 3 ca).

**Full pipeline** (v4-mix+rerank, cùng span với exp_0018 — chỉ đổi rule assertion):

| | exp_0018 (rule cũ) | exp_0023 (rule vá) |
|---|---|---|
| assert (dev) | 0.6607 | **0.6913** ↑ |
| text/cand | giống hệt | giống hệt (xác nhận chỉ đổi assertion) |

| **exp_0023 — ĐIỂM THẬT BTC** | 2026-07-17 | v4-mix + rerank + rule isHistorical đã vá, BTC | 38.6905 | **36.6015** | 23.4669 | **31.97440** | +0.22 so exp_0018 — **THẬT NHƯNG NHỎ HƠN NHIỀU** dev báo (dev dự đoán +3, thực tế +0.22). Công thức khớp lần 9 (31.97436≈31.97440). ⚠️ **BAN ĐẦU BỊ GÁN NHẦM SANG exp_0022** trong lần ghi log đầu (user báo nhầm số exp) — đã sửa sau khi user xác nhận lại. |
| **🏆 exp_0022 — ĐIỂM THẬT BTC (classifier)** | 2026-07-17 | v4-mix + rerank + **assertion CLASSIFIER**, BTC | **38.6905** | **39.3464** | **23.4669** | **32.79790** | 🏆 **BEST THẬT — không phải exp_0023**. Nguyên văn: `WER 61.3095 · J_assertion 39.3464 · J_candidates 23.4669`. WER & J_candidates giống hệt exp_0018/0023 (chỉ đổi assertion). **J_assertion +2.97 vs rule gốc — GẤP ~13 LẦN mức tăng của rule vá (+0.22)**. Công thức khớp (32.79783≈32.79790). |

### 🔴🔴 ĐẢO NGƯỢC LỚN: dev nói CLASSIFIER thua rule — BTC nói NGƯỢC LẠI, thắng đậm

Đây là sai lầm phương pháp nghiêm trọng nhất trong ngày: **quyết định "giữ rule, bỏ classifier" (dựa 100% trên dev) đã SAI**, và bị phát hiện muộn — sau khi cả 2 zip đã nộp và ban đầu bị BÁO CÁO NHẦM NHÃN (nghĩ điểm cao là exp_0023, thực ra là exp_0022).

| | dev assert | BTC J_assertion | BTC final |
|---|---|---|---|
| exp_0018 (rule gốc) | 0.6607 | 36.3798 | 31.90790 |
| exp_0023 (rule vá 2 bug cụ thể) | **0.6913** (dev: THẮNG NHIỀU) | 36.6015 (+0.22, ít hơn dev báo ~13×) | 31.97440 |
| exp_0022 (assertion classifier) | **0.6365** (dev: THUA) | **39.3464** (+2.97, **BEST**) | **32.79790** |

**Dev dự đoán SAI HƯỚNG cho classifier** — không chỉ sai độ lớn (như các case trước), mà sai cả DẤU. Đây là lần đầu tiên trong toàn bộ session dev đảo ngược hoàn toàn thứ hạng giữa 2 cấu hình CÙNG SPAN (cùng NER v4-mix, cùng matcher rerank, chỉ khác cơ chế gán assertion).

**Giả thuyết nguyên nhân** (chưa kiểm chứng được, dev/BTC gold khác nhau nên không truy sâu hơn): quyết định "classifier thua" dựa trên bóc tách 118 concept của dev — mẫu quá nhỏ để đại diện đúng phân phối 100 file BTC đầy đủ. Rule vá được suy ra TRỰC TIẾP từ quan sát lỗi trên chính dev gold (2 bug cụ thể tìm thấy khi soi 118 concept đó) — khả năng cao **rule vá bị fit theo đặc thù của dev sample**, trong khi classifier (train trên 280k template + 14k prose, đa dạng hơn nhiều) tổng quát tốt hơn trên phân phối thật của BTC dù cùng lúc đó lại kém hơn TRÊN CHÍNH dev sample nhỏ.

**Bài học phương pháp (bổ sung cho quy luật "cùng span → dev tin được")**: quy luật đó vẫn đúng cho candidates (kiểm chứng nhiều lần), nhưng **KHÔNG áp dụng an toàn cho lựa chọn giữa rule vs model học** khi rule được tinh chỉnh trực tiếp từ quan sát lỗi trên CHÍNH dev sample đó — nguy cơ overfit dev cao hơn tưởng. → Với thay đổi kiểu "rule quan sát-rồi-vá" vs "model train trên data lớn", **cần nộp BTC để phân xử**, không tin dev dù cùng span.

### ⚠️⚠️ exp_0018 PHÁ VỠ quy luật "cùng span → dev tin được" — cần thêm điều kiện

Đây là lần ĐẦU TIÊN trong ngày một so sánh cùng-span mà dev báo SAI HƯỚNG. Đối chiếu với mọi lần "cùng span → dev đúng" trước đó (exp_0003 vs 0005 vs 0006; exp_0007 vs 0008; exp_0010 vs 0012) — **tất cả đều đi kèm ĐỔI ABSTAIN RATE đáng kể** (coverage 49%→99%, hay 22%→8%/25%). Cơ chế "credit ảo từ abstain" chi phối CẢ dev lẫn BTC theo cùng hướng nên chúng khớp nhau — không phải vì dev đo đúng chất lượng candidate, mà vì cùng bị lệch bởi cùng 1 nguyên nhân.

exp_0018 khác: **abstain rate giữ NGUYÊN 22%=22%** (verify trực tiếp: cả 2 đều 117/540 abstain). Reranker chỉ đổi mã trong tập ĐÃ được gán, không đổi việc có gán hay không → cơ chế "credit ảo" KHÔNG có mặt ở đây. Phần dev đo được là hiệu ứng THẬT nhưng rất nhỏ (+1.3% trên BTC) — quá nhỏ để 15 file gold (lại INCOMPLETE) đo đúng dấu.

**→ Quy luật cập nhật**: "cùng span → dev tin được" chỉ áp dụng chắc chắn khi **abstain rate cũng đổi đáng kể theo**. Khi abstain rate giữ nguyên (chỉ đổi lựa chọn TRONG tập đã gán mã), dev mất độ tin cậy cho hiệu ứng nhỏ — cần BTC để phân xử. **Không áp dụng ngược lại cho exp_0016/exp_0017** (2 bản SapBERT fine-tune): ở đó abstain rate đổi mạnh (22%→25%/8%), nên cơ chế "credit ảo" vẫn chi phối và dev (cand giảm rõ 0.328/0.258, không phải hiệu ứng biên) nhiều khả năng vẫn đúng hướng — quyết định không nộp 2 bản đó vẫn hợp lý, KHÔNG bị lật bởi phát hiện này.

**Hệ quả thực dụng**: đổi default candidate matcher sang `RerankMatcher` cho các experiment tiếp theo (best đã biết). Nhưng cải tiến nhỏ (+0.12) — không phải đột phá, và bài học phương pháp (khi nào tin dev) quan trọng hơn bản thân điểm số.

| **exp_0019 — ĐIỂM THẬT BTC** | 2026-07-17 | NER **dense v6** (12k tpl + 2830 prose) + rerank, BTC | **37.0618** | **35.6874** | **24.3856** | **31.57900** | ❌ **< exp_0018 (v4-mix+rerank) 31.90790**. Nguyên văn: `WER 62.9382 · J_assertion 35.6874 · J_candidates 24.3856`. dense NER THUA v4-mix: text −1.63, assert −0.69, chỉ cand +0.92 → net −0.33. **→ v4-mix (6k tpl+prose) là NER base TỐT NHẤT; gấp đôi template (12k) làm TỆ text/assert.** |

### ⚠️⚠️ exp_0019 lật đổ khẳng định "dev text_score luôn so trực tiếp được" — SAI

Tôi từng nói dev text tin được khi đổi NER (vì không có cơ chế abstain). **exp_0019 chứng minh SAI:**

| | dev | BTC |
|---|---|---|
| dense text vs v4-mix text | 0.2577 > 0.2463 (dense CAO) | 37.06 < 38.69 (dense THẤP) |

Lý do: dev text chấm trên gold 15 file **thiếu nhãn** + là proxy soft-F1 (không phải WER thật). Khi NER đổi model → phân phối span đổi → số concept "thừa" so với gold thiếu bóp méo soft-F1. → **dev text CHỈ tin được khi span gần như không đổi (cùng NER, chỉ đổi matcher/threshold). Đổi hẳn NER model thì KHÔNG.**

🔑 **Tổng kết độ tin cậy của dev (sau 19 exp)**: dev KHÔNG tin được cho BẤT KỲ so sánh nào đổi NER model (cả 3 thành phần đều lệch). Chỉ tin được: (a) cùng NER + đổi matcher CÓ đổi abstain rate → cand đúng hướng; (b) KHÔNG tin khi abstain rate không đổi (§exp_0018). → **Hoàn thiện dev gold vẫn là chìa khoá gỡ nút này.**

### 🔬 exp_0015 tách confound của exp_0013: PROSE là driver, không phải việc giảm template

exp_0013 (6k tpl + prose) gộp 2 thay đổi so với exp_0010: (a) thêm prose, (b) giảm template 12k→6k. exp_0015 giữ **12k template** + thêm prose → cô lập yếu tố (b).

| | exp_0013 (6k tpl) | exp_0015 (12k tpl) |
|---|---|---|
| khớp gold thật | 45/64 | 43/64 |
| độ chính xác cand | 0.362 | 0.378 |
| span test CHẨN/THUỐC/KQ | 375/165/110 | 372/166/117 |
| dev text | 0.246 | 0.258 |

→ Gấp đôi template (6k→12k) **gần như không đổi hành vi** khi prose đã có mặt. **Kết luận: +3.16 của exp_0013 vs exp_0010 đến từ THÊM PROSE, không phải giảm template.** exp_0015 chỉ nhỉnh dev text (có thể do 2× template dạy biên cấu trúc tốt hơn chút) — biên độ nhỏ, chưa chắc vượt 31.79 trên BTC.

### ⚠️ exp_0013 vs exp_0010: dev đổi NER model → cand/assert KHÔNG so trực tiếp được, và lần này nhiễu CÓ HƯỚNG

Quy luật cũ ("span giống → dev tin được, span khác → dev sai") áp dụng ở đây theo chiều tệ hơn: nó không chỉ *không tin được*, mà còn **nhiễu có hướng che mất cải thiện thật**. Bóc tách numerator dev cand:

| | exp_0010 (v3-large) | exp_0013 (v4-mix) |
|---|---|---|
| concept khớp gold thật (trên 64 gold) | 38 | **45** — recall cao hơn |
| độ chính xác candidate TRÊN CHÚNG | 0.3307 | **0.3622** — chính xác hơn |
| concept thừa (rác) | 128 | **59** — over-predict giảm 54% |
| credit ảo từ abstain trên rác | 83.0 | 22.0 |
| **dev cand tổng** | 0.4902 | 0.3656 — **trông tệ hơn** |

**Cả 2 tín hiệu thật đều cho v4 thắng** (bắt nhiều hơn 38→45, chính xác hơn 0.33→0.36), nhưng dev cand tổng tụt vì v4 bớt bịa rác (128→59) nên mất credit ảo mà lẽ ra không nên tồn tại. Đây là hệ quả trực tiếp của giảm over-predict — một cải thiện thật — bị đọc nhầm thành thoái hoá vì cơ chế `J(∅,∅)=1` thưởng nhầm cho việc bịa nhiều rồi abstain.

`text_score` KHÔNG có cơ chế này (không có khái niệm "abstain" cho text) nên **so trực tiếp được**: 0.218→0.246, tăng thật.

→ **Cần BTC để biết v4 thật sự hơn hay kém exp_0010 (28.62340).** Dev không trả lời được câu này.

| **exp_0012 — ĐIỂM THẬT BTC** | 2026-07-15 | exp_0010 + sap_th=0.5, BTC | **34.0692** | **35.9491** | **13.2899** | **26.32140** | ❌ **< 28.62340**. Nguyên văn: `WER 65.9308 · J_assertion 35.9491 · J_candidates 13.2899`. WER & J_assertion **y hệt exp_0010** → đối chứng sạch tuyệt đối, mọi thay đổi chỉ từ candidates. 🔑 **cand TỤT 19.04→13.29 (−30%) khi coverage 49%→99%** ⇒ **ABSTAIN CÓ SINH ĐIỂM THẬT**. |

---

## 🔑 exp_0012: bằng chứng quyết định về `J(∅,∅)=1` — và một sai lầm đã được hoàn tác

**Kết luận**: BTC áp dụng **đúng chữ nghĩa** quy ước Jaccard, kể cả cho concept KHÔNG khớp gold. Concept thừa + candidate rỗng → **ăn 1.0 điểm**. Lưu ý "0 điểm cả 3 metric" trong đề **chỉ nói ca SAI TYPE** (text khớp gold, type khác), KHÔNG áp cho mọi false-positive.

**Hệ quả**: bài học *"abstention là lợi thế khi NER chưa sạch"* (ghi từ exp_0005) **ĐÚNG NGAY TỪ ĐẦU**. Sáng 2026-07-15 nó bị rút lại nhầm dựa trên một bản "sửa" metric sai; nay đã khôi phục.

**Bản "sửa" metric đã bị HOÀN TÁC.** Nó đổi concept thừa từ `J(∅,∅)=1` thành `0`, và điều đó phá đúng khả năng cần nhất:

| | dev (metric hiện tại) | dev (bản "đã sửa") | BTC thật |
|---|---|---|---|
| exp_0010 (th=0.7) | **0.4902** | 0.1647 | 19.0448 |
| exp_0012 (th=0.5) | **0.1725** | 0.1647 | 13.2899 |
| dự báo | **tụt 65%** ✅ | **bằng nhau** ❌ mù | tụt 30% ✅ |

**Bài học phương pháp (quan trọng nhất)**: bản "sửa" được biện minh bằng *độ khớp tuyệt đối* với BTC (dev 0.116 vs BTC 0.107, "lệch 6×"). Đó là **BẪY**. Metric nội bộ lệch xa BTC về giá trị tuyệt đối (0.49 vs 19.04) là **bình thường**; thứ duy nhất cần là **XẾP HẠNG đúng**. Con số 0.116≈0.107 chỉ là trùng hợp do gold thiếu nhãn triệt tiêu ngược lỗi vừa tạo ra. → **KHÔNG BAO GIỜ chỉnh metric theo độ khớp tuyệt đối.**

### ✅ Quy luật dùng dev cho candidate (kiểm chứng 4/4 nhóm)

> **Span GIỐNG HỆT nhau (chỉ đổi matcher) → dev xếp hạng candidate ĐÚNG. Span KHÁC nhau → dev SAI.**

| nhóm | dev xếp hạng |
|---|---|
| v2/min_conf.95/no-split: exp_0003 > exp_0006 > exp_0005 | ✅ đúng (BTC: 10.71 > 10.42 > 7.78) |
| v2/min_conf.95/split: exp_0007 > exp_0008 | ✅ đúng (BTC: 16.17 > 14.20) |
| v3-large: exp_0010 > exp_0012 | ✅ đúng (BTC: 19.04 > 13.29) |
| span khác (min_conf .95 vs .6): exp_0003 vs exp_0003b | ❌ **SAI** (dev nói 0003b hơn; BTC nói kém) |

Lý do: gold thiếu nhãn → concept thật bị coi là "thừa" → abstain trên chúng ăn credit ảo → **dev thưởng cho over-predict**. Nhưng nếu span cố định thì tập concept thừa cũng cố định → credit ảo thành **hằng số cộng**, triệt tiêu khi so sánh.

### ⚠️ Nhưng KHÔNG được ngoại suy quét ngưỡng trên dev

Quét `sap_th` trên dev (span cố định, v3-large): `0.50→0.1725 · 0.60→0.2706 · 0.70→0.4902 · 0.75→0.5451 · 0.80→0.5765 · 0.85→0.5804 · 0.90→0.5843` — **đơn điệu tăng, đỉnh ở 0.9**. **ĐỪNG TIN.** Dev có thiên lệch hệ thống ủng hộ abstain: gold thiếu nhãn → càng abstain càng nhiều credit ảo. Bằng chứng định lượng: dev bảo th=0.7 hơn th=0.5 **2.8×**, BTC chỉ nói **1.4×** → dev phóng đại lợi ích abstain đúng gấp đôi. Trên gold ĐẦY ĐỦ của BTC, các concept đó có mã thật → abstain ăn 0 chứ không ăn 1. → **đỉnh thật gần như chắc chắn THẤP HƠN 0.9; phải đo bằng BTC.**

Phân bố similarity SapBERT (939 span của exp_0010): `min 0.432 · p25 0.624 · median 0.698 · p75 0.801 · max 1.000`. Coverage: th=0.5→99% · 0.6→84% · **0.7→49%** · 0.75→36% · 0.8→26%.
| [exp_0011_v3large_nosplit](../experiments/exp_0011_v3large_nosplit/) | 2026-07-15 | exp_0010 + tắt `split_newlines` | 0.213 | 0.212 | 0.127 | 0.178 | ❌ Tệ hơn exp_0010 rõ (cand 0.127 vs 0.165). Dev nhất quán trên CẢ 2 model NER: **split_newlines giúp cand**. Không nộp. |

> ⚠️ **Mâu thuẫn dev↔BTC chưa giải quyết về `split_newlines`**: dev nói split GIÚP assert (0.2165 vs 0.2086); BTC nói split HẠI assert (30.14 vs 31.03). Dev đồng ý BTC về text. Nghi phạm: gold dev thiếu occurrence → assert dev không tin được. exp_0009 là phép A/B sạch để chốt.
>
> ⚠️ **dev cand KHÔNG ngoại suy được sang BTC theo giá trị tuyệt đối**: exp_0003/0005/0006/0008 đều có dev cand ≈0.116 nhưng BTC trải từ **7.78 → 14.20**. Dev chỉ dùng để **xếp hạng trong cùng họ cấu hình**, không để dự đoán điểm BTC.

---

## ⚠️ Lỗi metric đã sửa (2026-07-15) — đọc trước khi so điểm dev cũ

`src/eval/metric.py` từng cho concept **KHÔNG ghép được** ăn quy ước `J(∅,∅)=1.0`, ở **cả 2 phía**:
- **pred thừa** (NER bịa ra) + candidate abstain (`[]`) → `J([], [])` = **+1.0 điểm miễn phí**;
- **gold bỏ sót** (không phát hiện) mà gold assertions rỗng → cũng **+1.0**.

Trái với lưu ý đề: concept không khớp "bị tính 2 lần ... **mỗi lần đều được tính 0 điểm với cả 3 loại metric**". Quy ước `J(∅,∅)=1` chỉ dành cho concept **có thật, đã ghép** mà gold không có mã.

**Mức độ méo** (bóc tách numerator dev): với exp_0007, **80.0/118.0 = 68%** điểm candidate đến từ concept rác abstain; exp_0003 là 65.0/94.7 = 69%. Đo trên assertions cũng vậy: 66% số lần chấm là concept thừa, ăn trung bình 0.590/lần.

**Bằng chứng bản sửa đúng hơn** — dev candidate sau sửa bám sát điểm BTC thật:

| exp | dev cand CŨ | dev cand SAU SỬA | BTC thật | lệch (sau sửa) |
|---|---|---|---|---|
| exp_0001 | 0.207 | 0.143 | 0.096 | 0.047 |
| exp_0003 | 0.371 | 0.116 | 0.107 | **0.009** |
| exp_0003b | — | 0.081 | 0.095 | 0.014 |
| exp_0005 | 0.116 | 0.116 | 0.078 | 0.038 |
| exp_0006 | 0.312 | 0.116 | 0.104 | **0.012** |

→ sai số tuyệt đối trung bình giảm từ ~0.155 xuống ~0.026 (**~6×**).

### 🔑 Ba bài học rút ra

1. **Bài học "abstention là lợi thế" trước đây là SAI** — nó là artifact của metric lỗi. Abstain không sinh điểm; nó chỉ *tránh bị phạt*. Ưu thế thật của SapBERT là **gán mã đúng hơn fuzzy trên concept có thật** (0.147/0.133 vs 0.116) — kết luận cũ đúng hướng nhưng **đúng vì lý do khác**.
2. **Hai lỗi cũ triệt tiêu nhau** → che mất bản chất: metric lỗi *thổi phồng* dev, gold thiếu occurrence *dìm* dev. Vì vậy "dev báo text tụt nhưng BTC tăng" **không chỉ** do gold thiếu như đã ghi trước đây.
3. **dev vẫn CHƯA xếp hạng đúng** (baseline 0.143 > exp_0003 0.116, nhưng BTC nói ngược: 0.096 < 0.107) vì gold còn thiếu occurrence → concept thật bị tính là "thừa". Sửa metric mới chỉ chữa được **giá trị tuyệt đối**; muốn dev **xếp hạng** tin cậy thì **bắt buộc hoàn thiện dev gold**. → ưu tiên #1 hiện tại.

Chấm lại mọi exp từ predictions đã lưu (không cần model weights): `python scripts/rescore_all.py [--write]`.

---

## Cách thêm 1 experiment mới vào bảng trên

1. Tạo folder `experiments/exp_XXXX_<tên-ngắn-gọn>/` (xem `experiments/README.md`).
2. Chạy pipeline, sinh `predictions/*.json`, chạy `src/eval/` để ra `metrics.json`.
3. Thêm 1 dòng vào bảng trên, link tới folder experiment.
4. Nếu experiment dẫn tới thay đổi hướng đi, cập nhật [IDEAS.md](IDEAS.md) (mục ý tưởng đã thử/loại bỏ).
