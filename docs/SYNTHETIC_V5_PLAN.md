# SYNTHETIC v5 — Kế hoạch xây lại bộ dữ liệu train (quality-first)

> Kế hoạch thiết kế lại `data/synthetic/` theo hướng **ít mẫu, chất lượng cao**, thay cho v4-mix
> (8.830 doc / 203.635 entity). Nối tiếp [DATA_PLAN.md](DATA_PLAN.md) (chiến lược gốc) và
> [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) (kết quả đã đo). Đọc [IDEAS.md](IDEAS.md) trước.
>
> Nguồn ý tưởng: JMIR 2025 (synthetic + LLM annotation), OpenBioNER v1/v2 (description,
> entity masking, curriculum quality-first), cùng các phép đo nội bộ ghi trong file này.

---

## 0. TL;DR — chốt gì, đổi gì

| Quyết định | Trạng thái |
|---|---|
| Giảm còn ~1.000 doc, quét learning curve 100/500/700/1000 | ✅ theo, **nhưng đo bằng ENTITY/WINDOW, không phải doc**, và **bắt buộc có mốc neo cao** |
| Nới luật leakage: paraphrase từ 100 file test | ✅ theo, **có 4 điều kiện cứng** (§2) |
| Entity-first + câu hoàn chỉnh kèm assertion | ✅ theo, **nâng cấp bằng verifier xác định** thay vì viết tay template |
| **Chốt boundary convention TRƯỚC khi sinh** | 🆕 **bắt buộc, việc #0** — nếu bỏ qua, 1.000 mẫu "chất lượng cao" sẽ bake-in mâu thuẫn |

---

## 1. Phản biện đề xuất "1.000 mẫu là đủ"

### 1.1. Con số +35.6 F1 của OpenBioNER đang bị đọc sai

Paper v1 §7.1 báo lợi ích theo số sample đích: `100 → +35.6 F1`, `500 → +3.4`, `1000 → +1.2`,
`full → +0.2`. **Đây là khoảng cách giữa "có description-pretraining" và "không có"**, KHÔNG
phải hiệu năng tuyệt đối. Nhìn Figure 4 của họ: hiệu năng tuyệt đối vẫn đi từ ~60 F1 (100 mẫu)
lên ~85 F1 (full data). Tức **thêm dữ liệu vẫn tăng điểm mạnh**; chỉ có *lợi thế của pretraining*
là tan biến.

→ Không thể dùng con số này để kết luận "1.000 mẫu là đủ".

### 1.2. Bằng chứng ĐÚNG cho việc giảm volume nằm ở chỗ khác

Hai nguồn hợp lệ:

- **JMIR 2025**: hiệu năng đạt đỉnh ở **1.000–2.000 document**, thêm nữa thì đi ngang hoặc *giảm*
  ("adding more data just creates more noise").
- **Nội bộ (exp_0019)**: `12k template + 2.830 prose` (=14.830) **THUA** `6k + 2.830` (=8.830):
  final 31.579 vs 31.908. Đã có bằng chứng thật rằng tăng volume không giúp.

### 1.3. ⚠️ Bẫy đơn vị: "document" của ta ≠ "document" của paper

| | doc | ký tự/doc | window (maxlen 256) | entity/doc |
|---|---|---|---|---|
| v4-mix hiện tại | 8.830 | ~1.277 | ~2 | ~23 |
| **1.000 doc theo đề xuất** | 1.000 | ~1.277 | ~2.000 window | ~23.000 entity |
| JMIR "2.000 documents" | 2.000 | ngắn hơn nhiều | ~1 | vài entity |

→ **Luôn báo cáo learning curve theo `#entity` và `#window`, không chỉ `#doc`.** 1.000 doc của ta
vẫn là ~23k entity — không hề nhỏ.

### 1.4. Bắt buộc có mốc neo cao

Learning curve `100/500/700/1000` **thiếu điểm neo trên**. Nếu tất cả các mốc đều tệ hơn v4-mix,
ta sẽ không biết, vì không có mốc nào để so. → thêm **`v4-mix hiện tại (8.830)` làm control**, và
lý tưởng là thêm `2000` để thấy đỉnh nằm đâu.

**Lý do THẬT SỰ nên giảm volume** (và tôi đồng ý): *chi phí đầu tư trên mỗi mẫu tỉ lệ nghịch với
số mẫu*. Với 1.000 mẫu ta có thể chi trả: nhiều lần sinh + lọc, verifier chạy trên từng mẫu,
review tay một phần, prompt giàu hơn. Đó mới là lập luận đúng — không phải "paper nói 100 mẫu là đủ".

---

## 2. Phản biện đề xuất "nới luật leakage"

### 2.1. Mâu thuẫn nội tại trong lý do

Lý do đưa ra: *"BTC sắp nâng cấp đề, 100 file test này có thể không còn dùng"*. Nhưng nếu tập test
đổi thật, thì dữ liệu **paraphrase từ tập test CŨ chính là thứ mất giá trị đầu tiên**. Lý do này
biện minh cho việc *ít đầu tư* vào paraphrase, không phải *nhiều hơn*.

### 2.2. Nhưng có một lập luận KHÁC, mạnh hơn, ủng hộ paraphrase

Thứ đáng học từ tập test **không phải nội dung y khoa cụ thể**, mà là **thể loại văn bản**:
bệnh án tiếng Anh dịch máy sang tiếng Việt, nhồi vào khung mục cố định, kèm nhiễu đặc trưng
(dịch hỏng kiểu `"Các tập kinh lâm sàng"`, double-space, token dính liền). Nếu private test
**cùng generator** — khả năng rất cao — thì thể loại này **vẫn giữ nguyên** dù file cụ thể đổi.

→ **Trích XUẤT PHONG CÁCH/CẤU TRÚC, không trích nội dung.** Đây là ranh giới quyết định.

### 2.3. Về luật thi (đọc kỹ trước khi làm)

Đề cấm đúng 3 điều: (1) hard-code output theo file test; (2) dùng LLM ngoài/API **sinh ra output**;
(3) người gán nhãn tay tập test rồi nộp. **Paraphrase input công khai, không nhãn, để làm data
train — không thuộc điều nào.** Đây là *transductive learning*, chuẩn mực phổ biến trong ML
competition khi test input được phát công khai.

**Lằn ranh TUYỆT ĐỐI không được vượt**: không bao giờ suy ra **nhãn** cho file test từ chính
file test rồi nộp nhãn đó. Paraphrase → text MỚI → ta tự gán nhãn → train model → model tự
sinh output. Chuỗi này giữ nguyên tính liêm chính.

### 2.4. Bốn điều kiện cứng nếu làm

1. **LCS gate là tiêu chí LOẠI, không phải audit sau**: mọi doc sinh ra phải có
   `max LCS ratio với mọi file test < 0.5` (paper JMIR dùng ngưỡng ~0.6–0.7 để coi là copy;
   ta chặt hơn). Doc vượt ngưỡng → **vứt, sinh lại**.
2. **n-gram gate**: không doc nào được chứa n-gram ≥ 10 từ trùng nguyên văn test.
3. **Chỉ mượn KHUNG, entity phải từ KB**: tên bệnh/thuốc lấy từ ICD-10/RxNorm như hiện tại,
   **không** lấy entity xuất hiện trong test → tránh học phân phối bệnh của test.
4. **Giữ nhánh control không-paraphrase** để A/B. Nếu paraphrase không thắng rõ, bỏ — vì nó là
   nhánh rủi ro nhất khi đề đổi.

### 2.5. Ghi vào README nộp bài

Ghi rõ: *"synthetic được sinh từ template tự viết + LLM self-host; tập test công khai (không nhãn)
được dùng làm tham chiếu phong cách; mọi mẫu qua LCS gate < 0.5"*. Minh bạch chủ động tốt hơn
để BTC tự phát hiện.

**Số liệu nền hiện tại** (đã đo, dùng làm mốc so sánh cho v5):

| | n-gram-13 trùng test | LCS ratio cao nhất |
|---|---|---|
| template v3 | 248/3.446.460 = 0.0072% | 0.394 |
| prose (Qwen) | 0/156.149 = **0.0000%** | 0.407 |

---

## 3. 🚨 Việc #0 — CHỐT BOUNDARY CONVENTION (bắt buộc trước khi sinh)

Đây là việc tôi bổ sung, và tôi cho là **quan trọng hơn cả hai đề xuất trên**.

### 3.1. Bằng chứng: convention hiện tại đang mâu thuẫn ở 3 nơi

**(a) 25% span bắt đúng loại lại sai biên** (đo trên exp_0022 vs dev gold): 31/126. Lỗi biên
không phải lỗi recall — model đã thấy khái niệm, chỉ không biết cụm từ *kết thúc ở đâu*.

Bốn kiểu lỗi biên đã quan sát:
```
nuốt thừa   : 'Bệnh thận đa nang'    → 'Bệnh thận đa nang (tiền sử'
              'prograf'              → 'prograf (dose decreased from 5mg bid to '
cắt cụt     : 'buồn nôn và nôn'      → 'buồn nôn'
mất đầu     : 'rối loạn lo âu'       → 'âu'
cắt giữa số : '5.8' → '8.'   |   '0.10' → '10'   |   '6.3' → '3, mẫu không tan máu'
```

**(b) Dev gold của TA tự mâu thuẫn**: 8/54 `TRIỆU_CHỨNG` giữ bổ ngữ mức độ
(`'Ngứa da toàn thân nhiều'`, `'nghẹt mũi nhiều hơn'`, `'mất trí nhớ chi tiết'`), số còn lại thì
không. Không có quy tắc nào phân biệt.

**(c) Convention THUỐC lệch giữa 4 nguồn** — nghiêm trọng nhất:

| nguồn | span có LIỀU | có ĐƯỜNG DÙNG |
|---|---|---|
| **Ví dụ ĐỀ BÀI (gold thật BTC)** | **100%** (`'amlodipine 10 mg po daily'`) | **100%** |
| synthetic template (train) | 60.3% | 42.0% |
| synthetic prose | 47.3% | 29.4% |
| **dev gold (ta tự gán)** | **15.0%** | **5.0%** |
| predictions exp_0022 | 13.3% | 10.3% |

→ Dev gold của ta **ngược hẳn** convention của đề. Ta đang chấm model bằng một thước lệch.

⚠️ **Đính chính để không thổi phồng**: trên 100 file test thật chỉ có **33 cụm "tên + liều"** và
39/2.989 dòng có liều. Chỉ **1/165** span thuốc ta dự đoán có liều đứng ngay sau. Nên đây **không
phải mỏ vàng điểm số** — nhưng nó *là* bằng chứng convention chưa được chốt, và nó cảnh báo một
lỗi thiết kế synthetic ở §3.3.

### 3.2. Sản phẩm cần có: `docs/ANNOTATION_GUIDELINE.md`

Học cấu trúc description của OpenBioNER (§9.1 Debate doc), mỗi type gồm 6 mục:

```
1. Phạm vi ngữ nghĩa   — type này là gì
2. Bao gồm             — cụm nào được tính
3. Loại trừ            — cụm gần nghĩa nào thuộc type khác
4. Quy tắc BIÊN        — bổ ngữ/số/đơn vị/liều/đường dùng có nằm trong span không
5. Ví dụ dương         — lấy từ ví dụ đề bài (nguồn chuẩn duy nhất)
6. Nhầm lẫn khó        — CHẨN_ĐOÁN vs TRIỆU_CHỨNG; TÊN_XN vs KẾT_QUẢ_XN
```

**Nguồn chuẩn khi mâu thuẫn: ví dụ trong `TASK/de_bai_chi_tiet.md`, không phải trực giác của ta.**

### 3.3. Lỗi thiết kế synthetic phát hiện kèm

Synthetic train có **60% span thuốc kèm liều**, trong khi test chỉ có ~20% cơ hội có liều.
Model được dạy "thuốc thường có liều đi kèm" → khi gặp thuốc trần trên test, có xu hướng
**với tay ra ngoài** tìm liều → đúng kiểu lỗi `'prograf (dose decreased from 5mg bid to '`.
→ v5 phải khớp tỉ lệ này với phân phối test.

---

## 4. Kiến trúc sinh dữ liệu v5

### 4.1. Nguyên tắc: nhãn là SẢN PHẨM PHỤ của việc dựng chuỗi, không phải kết quả đoán ngược

Giữ nguyên thế mạnh lớn nhất hiện có — đã đo: **100.00% đúng span/type, 0 lỗi offset trên
203.635 entity**, so với JMIR paper phải chấp nhận nhãn F1 0.44–0.75 vì họ sinh text trước rồi
mới đoán nhãn ngược.

### 4.2. Luồng 5 tầng

```
[1] BỘ KHUNG (structure bank)
    ├─ khung mục + kiểu dòng, TỰ VIẾT hoặc paraphrase-có-gate từ test
    └─ gán metadata: genre, section, mật độ entity, mix assertion
                 ↓
[2] KẾ HOẠCH MẪU (sample plan)  ← entity-first, NÂNG CẤP: kèm assertion + vai trò câu
    ├─ chọn entity từ KB (ICD/RxNorm) + lexicon
    ├─ chọn assertion CHỦ ĐÍCH cho từng entity
    └─ chọn "khuôn câu" mang assertion đó
                 ↓
[3] SINH TEXT
    ├─ template xác định  → nhãn chắc chắn đúng, đa dạng thấp
    └─ Qwen2.5-7B local   → đa dạng cao, cần verify
                 ↓
[4] GÁN NHÃN + VERIFY  (đây là tầng mới, quan trọng nhất)
    ├─ locate offset (đã có, case-insensitive, lấy chuỗi THẬT)
    ├─ sweep entity LLM tự thêm (SapBERT thay lexicon — xem §5.4)
    ├─ ✅ VERIFIER ASSERTION xác định  ← §5.3
    └─ ✅ VERIFIER BIÊN theo guideline  ← §5.2
                 ↓
[5] CỔNG CHẤT LƯỢNG (quality gate)
    ├─ offset invariant: raw[s:e] == text     (cứng, đã có)
    ├─ LCS < 0.5 vs mọi file test             (cứng, mới)
    ├─ n-gram-10 không trùng test             (cứng, mới)
    ├─ phủ đủ 5 type, có KẾT_QUẢ_XÉT_NGHIỆM   (cứng, mới)
    └─ provenance mỗi nhãn: planned|sweep|llm|human
```

### 4.3. Vì sao thêm tầng [4]

Nhãn `assertions` hiện là thứ **ta YÊU CẦU** LLM, không phải thứ nó **thật sự viết**. Đã đo trên
prose: `isNegated` chỉ khớp **~59%**, `isHistorical` ~69%. Span/type thì chắc chắn đúng (ta tìm
thấy chuỗi), nhưng assertion thì không. Với `J_assertion` chiếm weight 0.3, đây là lỗ hổng thật.

---

## 5. Các idea cụ thể

Mỗi idea: **vấn đề → cách làm → cách đo → rủi ro**.

### IDEA 1 — Chốt guideline + verifier biên  ⭐ ưu tiên cao nhất

- **Vấn đề**: 25% span đúng type nhưng sai biên; dev gold tự mâu thuẫn; convention thuốc lệch đề.
- **Cách làm**: viết `docs/ANNOTATION_GUIDELINE.md` (§3.2) → viết `verify_boundary()` kiểm tra
  span synthetic có tuân guideline không → chạy trên v4-mix để đo mức vi phạm hiện tại.
- **Đo**: % span synthetic vi phạm guideline; sau đó exact-vs-boundary trên dev.
- **Rủi ro**: chốt sai convention → sai toàn hệ thống. Giảm bằng cách **chỉ lấy chuẩn từ ví dụ đề**,
  ghi rõ chỗ chưa chắc thay vì đoán.

### IDEA 2 — Sửa 2 bug hậu xử lý biên (rẻ, độc lập với data)

- **Vấn đề**: `'5.8' → '8.'` (cắt giữa số thập phân); `'prograf (dose decreased…'` (nuốt ngoặc).
- **Cách làm**: `_snap_word` bảo vệ `\d+[.,]\d+`; port `_trim_drug()` từ rule extractor sang
  `ner_extractor`.
- **Đo**: đếm lại 4 nhóm lỗi biên trên cùng predictions — phải giảm nhóm "cắt giữa số" về ~0.
- **Rủi ro**: thấp. Không đụng model, chạy lại inference là xong.
- **Lưu ý**: đây là thay đổi **span** → dev sẽ xếp hạng sai candidate; so bằng `text_score`.

### IDEA 3 — Câu hoàn chỉnh mang assertion + verifier xác định  ⭐ (nâng cấp đề xuất của bạn)

- **Vấn đề**: nhãn assertion nhiễu (isNegated 59%).
- **Cách làm** — *không* viết tay template (mất đa dạng, quay lại lỗi Cấp 2). Thay bằng:
  1. Chọn trước `(entity, assertion)`;
  2. Cho Qwen sinh câu, prompt kèm **định nghĩa assertion + ví dụ đúng/sai** (học từ
     description richness của OpenBioNER v2: bước nhảy lớn nhất là *name-only → concise definition*);
  3. **Verifier xác định** đọc lại text sinh ra, dò cue trong cửa sổ hẹp quanh span;
  4. **Chỉ giữ mẫu mà `assertion kế hoạch == assertion phát hiện`**; lệch → vứt hoặc gán lại theo
     cái phát hiện được.
- **Đo**: tỉ lệ khớp assertion trước/sau verifier (mục tiêu >90% từ mức 59%); sau đó `J_assertion` BTC.
- **Rủi ro**: verifier dùng cùng cue-set với `rules.py` → nếu rule sai thì nhãn cũng sai theo.
  Giảm bằng cách verifier dùng **cửa sổ hẹp** (không phải cả dòng như `_line_around`) và cue-set
  rộng hơn rule.

### IDEA 4 — Phủ đủ 5 type, đặc biệt `KẾT_QUẢ_XÉT_NGHIỆM`

- **Vấn đề**: prose hiện có **0** entity `KẾT_QUẢ_XÉT_NGHIỆM` (đo được). exp_0014 (prose-only)
  từng sụp vì thiếu type này.
- **Cách làm**: thêm khuôn sinh cặp `TÊN_XÉT_NGHIỆM ↔ KẾT_QUẢ_XÉT_NGHIỆM` trong văn xuôi
  (không chỉ dạng bảng), khớp phân phối test.
- **Đo**: phân bố type synthetic vs phân bố type trong dev gold.

### IDEA 5 — Khớp phân phối bề mặt với test (không phải nội dung)

- **Vấn đề đã đo**: liều thuốc synthetic 60% vs test ~20%; độ dài doc đã khớp (1277 vs 1229);
  nhiễu glue synthetic 40% vs test 27%.
- **Cách làm**: tham số hoá các tỉ lệ này, canh theo thống kê bề mặt của test (chỉ thống kê, không
  copy nội dung).
- **Đo**: bảng so phân phối synthetic vs test cho: độ dài, glue%, liều%, entity/1000 ký tự, %doc
  có mỗi type.

### IDEA 6 — Entity masking (OpenBioNER)

- **Vấn đề**: model học thuộc canonical name + template slot (val F1 0.9998 = vô nghĩa).
- **Cách làm**: mask toàn bộ mention thành `[MASK]` với xác suất `p` lúc train. A/B `p = 0/0.1/0.3`.
- **Đo**: `text_score` trên dev (so trực tiếp được); lỗi trên surface form hiếm; FP ở ngữ cảnh
  giống template.
- **Rủi ro**: **không copy `p=0.5`** của paper. `KẾT_QUẢ_XÉT_NGHIỆM` (số + đơn vị) và `THUỐC`
  phụ thuộc mạnh vào surface form → mask nhiều sẽ dạy model đoán bừa. Vòng 2 mới thử mask
  **theo type** (cao cho CHẨN_ĐOÁN/TRIỆU_CHỨNG, thấp cho 2 type kia).

### IDEA 7 — Transductive: khai thác pattern từ 100 file test ⭐ (chi tiết đầy đủ)

> Nguyên tắc xuyên suốt: **lấy KHUNG (cách viết), không lấy NỘI DUNG (viết về cái gì).**
> Entity luôn đến từ KB. Đây là ranh giới quyết định giữa hợp lệ và overfit.

#### Tầng 1 — Bộ xương tài liệu (skeleton)

Header xuất hiện ≥5 file (đã trích được, **không chứa entity nào**):

```
 56×  3. Đánh giá tại bệnh viện        27×  Đặc điểm triệu chứng
 51×  2. Tiền sử bệnh hiện tại         22×  Diễn biến bệnh
 38×  1. Tiền sử bệnh                  18×  Các bệnh lý mãn tính
 35×  1. Tiền sử bệnh nội khoa         16×  Các thủ thuật đã thực hiện
 33×  Triệu chứng hiện tại             16×  Kết quả xét nghiệm
```

→ Dùng làm **khung tài liệu** + xác suất chuyển mục. Đây thuần là *layout*, không phải tri thức
y khoa của tập test.

#### Tầng 2 — Phân bố kiểu dòng (đã đo, dùng để canh generator)

| kiểu dòng | tỉ lệ |
|---|---|
| bullet (`- `, `* `) | **58.2%** |
| dòng ngắn khác | 17.7% |
| `nhãn: giá trị` | 11.3% |
| đánh số (`1. `) | 9.5% |
| **văn xuôi dài (>18 từ)** | **2.1%** |
| `nhãn:` rỗng | 1.3% |

⚠️ **Phát hiện quan trọng**: văn xuôi dài chỉ **2.1%**. Prose Qwen hiện chiếm ~32% tổng entity của
train_mix → **ta đang train lệch nặng về prose so với thực tế**. v5 phải canh lại tỉ lệ này.

#### Tầng 3 — Khung câu (frame mining) ⭐ phần giá trị nhất

Dùng **chính predictions của ta** để định vị entity → đục lỗ thành slot → phần còn lại là khung
tái dùng được. Đã trích **724 khung duy nhất**:

```
165×  - {CHẨN_ĐOÁN}                       6×  - được cho {THUỐC}
122×  - {TRIỆU_CHỨNG}                      5×  - {TÊN_XÉT_NGHIỆM} cho thấy {CHẨN_ĐOÁN}
 26×  - {THUỐC}                            5×  Bệnh lý mãn tính: {CHẨN_ĐOÁN}
 18×  - Không {TRIỆU_CHỨNG}                4×  - {TÊN_XÉT_NGHIỆM} là {KẾT_QUẢ_XÉT_NGHIỆM}
 17×  - {TÊN_XÉT_NGHIỆM} {KẾT_QUẢ_XÉT_NGHIỆM}   3×  Thuốc trước khi nhập viện: {THUỐC}
 14×  Lý do nhập viện: {TRIỆU_CHỨNG}       3×  - phủ nhận {TRIỆU_CHỨNG}
  8×  Lý do nhập viện: {CHẨN_ĐOÁN}         3×  - **{TRIỆU_CHỨNG}:**
```

Khung bắt được **4 thứ template tự viết không có**:
1. **Vị trí cue phủ định thật**: `- Không {TRIỆU_CHỨNG}`, `- phủ nhận {TRIỆU_CHỨNG}` — khác hẳn
   `"Bệnh nhân không ghi nhận X"` mà ta đang sinh.
2. **Cách ghép cặp lab**: `{TÊN_XÉT_NGHIỆM} {KẾT_QUẢ_XÉT_NGHIỆM}` không dấu phân cách.
3. **Artifact markdown thật**: `- **{TRIỆU_CHỨNG}:**`.
4. **Mật độ slot/dòng thật**: đa số 1 slot/dòng, không phải dòng dày đặc như template.

**Quy trình dùng**: chọn khung theo tần suất → điền slot bằng entity KB → nhãn = vị trí slot,
**chính xác tuyệt đối theo thiết kế** (không cần dò lại).

⚠️ **Khung đến từ predictions của ta nên MANG THEO LỖI của ta.** Ví dụ `- {CHẨN_ĐOÁN} {CHẨN_ĐOÁN}`
(3×) rất có thể là artifact của lỗi tách span, không phải hiện tượng thật. → **phải lọc**: bỏ khung
tần suất 1, bỏ khung có ≥2 slot cùng type liền nhau, và review tay top-50 khung.

#### Tầng 4 — Nhiễu bề mặt

Chỉ lấy **thống kê**, không lấy chuỗi: tỉ lệ doc có token dính liền (27%), double-space, độ dài
doc (median 1229), phân bố ký tự/dòng. Đã có sẵn trong `notebooks/eda_features.py`.

#### Ranh giới — cái gì KHÔNG lấy

| lấy ✅ | không lấy ❌ |
|---|---|
| header, layout, kiểu dòng | tên bệnh/thuốc cụ thể xuất hiện trong test |
| khung câu đã đục lỗ entity | câu nguyên văn còn entity |
| thống kê nhiễu/độ dài | đoạn văn ≥10 từ liên tiếp |
| vị trí/kiểu cue assertion | phân phối bệnh của test (→ sẽ là overfit thật) |

**Vì sao ranh giới này quan trọng**: học *phân phối bệnh* của public test = tối ưu vào đúng 100
file đó → sập khi đổi đề. Học *cách viết* = học generator của BTC → **giữ giá trị kể cả khi file
đổi**, vì private test gần như chắc chắn cùng generator.

#### Cổng kiểm soát (bắt buộc, xem §2.4)

`LCS < 0.5` + `không n-gram ≥10 từ trùng` + `entity chỉ từ KB` + **luôn giữ nhánh control
không-transductive để A/B**.

- **Đo**: A/B với control cùng số mẫu; báo cả LCS/n-gram sau khi sinh.
- **Rủi ro**: mất giá trị nếu BTC đổi generator (không chỉ đổi file). Giữ control để phát hiện.

### IDEA 8 — Learning curve đúng cách

- **Cách làm**: giữ **cố định** model/seed/config, chỉ đổi lượng data:
  `100 / 500 / 700 / 1000 / 2000 / 8830(control v4-mix)`.
- **Đo**: báo theo `#doc`, `#window`, `#entity`; chấm `text_score` trên dev (so trực tiếp được),
  và bóc tách numerator cho candidate.
- **Rủi ro**: một seed không đủ kết luận. Nếu 2 mốc sát nhau, chạy thêm seed trước khi chốt.

---

## 6. Hướng tôi đề xuất THÊM (ngoài 3 điểm của bạn)

### 6.1. Provenance cho từng nhãn

Mỗi concept lưu `"src": "planned" | "sweep" | "llm" | "human"`. Cho phép sau này ablate: "bỏ nhãn
`sweep` đi thì điểm đổi thế nào?" — không có provenance thì không trả lời được.

### 6.2. Thay lexicon-sweep bằng SapBERT-sweep

Sweep hiện dùng exact-match trên lexicon cứng (84 triệu chứng + 52 xét nghiệm). Ta đã có tín hiệu
**độc lập và xác định** cho `CHẨN_ĐOÁN`/`THUỐC`: SapBERT + KB. Dùng nó bắt entity LLM tự thêm —
rẻ hơn gọi LLM lần hai, và **không bị lỗi tương quan** (Qwen đọc lại text Qwen viết sẽ tự xác nhận
hallucination của chính nó).

### 6.3. Giữ một holdout thật, tách khỏi dev 15 file

Hiện mọi quyết định đều đo trên đúng 15 file. Rủi ro overfit vào chính 15 file đó là thật (đã xảy
ra một lần: rule vá `isHistorical` được chẩn đoán trên dev rồi dev báo +3, BTC thật chỉ +0.22).
→ tách vài file làm holdout, chỉ đụng khi chốt.

### 6.4. Không sinh data cho khối candidate bằng LLM

`cand 23.47` (weight 0.4) vẫn thấp nhất, nhưng dữ liệu train cho reranker **đã có sẵn miễn phí**:
**211.890 cặp (variant, variant) cùng mã** từ chính KB (ICD 15.844 + RxNorm 196.046). Không cần
LLM sinh. Đây là hướng riêng, không nằm trong v5 data plan.

---

## 7. TODO — theo phase, mỗi mục có tiêu chí đo

### Phase 0 — Nền (bắt buộc trước khi sinh 1 dòng data nào)

- [ ] **0.1** Viết `docs/ANNOTATION_GUIDELINE.md` cho 5 type, 6 mục mỗi type (§3.2).
      *Đo*: mọi ca lỗi biên trong §3.1 phải tra được ra một quy tắc.
- [ ] **0.2** Chốt convention `THUỐC` (có/không liều+đường dùng) theo ví dụ đề.
      *Đo*: quyết định được ghi rõ + lý do; cập nhật generator cho khớp.
- [ ] **0.3** Viết `scripts/audit_synthetic.py`: LCS gate, n-gram gate, phân bố type/độ dài/nhiễu,
      offset invariant. *Đo*: chạy được trên v4-mix, in bảng nền để so.
- [ ] **0.4** Viết `scripts/diagnose_boundary.py`: bảng exact / sai-biên / sai-type / miss / thừa,
      tách theo type. *Đo*: tái tạo được con số 25% đã đo.
- [ ] **0.5** Sửa dev gold theo guideline mới (ưu tiên 20 span `THUỐC` + 8 span có bổ ngữ).
      *Đo*: gold nhất quán 100% với guideline.

### Phase 1 — Sửa rẻ, độc lập data (làm song song Phase 0)

- [ ] **1.1** Sửa `_snap_word` bảo vệ số thập phân. *Đo*: nhóm "cắt giữa số" → 0.
- [ ] **1.2** Port `_trim_drug()` sang `ner_extractor`. *Đo*: nhóm "nuốt ngoặc" giảm.
- [ ] **1.3** Chạy lại pipeline + `diagnose_boundary`. *Đo*: `text_score` dev tăng; nếu tăng rõ → nộp BTC.

### Phase 2 — Sinh v5

- [ ] **2.1** Structure bank + metadata (genre/section/mật độ/assertion mix).
- [ ] **2.2** Sample plan entity-first **kèm assertion chủ đích** (IDEA 3 bước 1–2).
- [ ] **2.3** Verifier assertion xác định (IDEA 3 bước 3–4).
      *Đo*: khớp assertion 59% → mục tiêu >90%.
- [ ] **2.4** Verifier biên theo guideline. *Đo*: % span vi phạm → ~0.
- [ ] **2.5** Phủ `KẾT_QUẢ_XÉT_NGHIỆM` trong prose. *Đo*: >0, khớp phân phối dev.
- [ ] **2.6** Khớp phân phối bề mặt (liều/glue/độ dài). *Đo*: bảng so §IDEA 5.
- [ ] **2.7** Provenance cho từng nhãn. *Đo*: field `src` có mặt 100%.
- [ ] **2.8** Sinh 1.000 doc + chạy `audit_synthetic`. *Đo*: qua toàn bộ gate cứng.

### Phase 3 — Learning curve + ablation

- [ ] **3.1** Train `100/500/700/1000` (+ **control 8830**), cố định seed/config.
      *Đo*: bảng `#doc/#window/#entity` × `text_score dev`.
- [ ] **3.2** Chọn mốc tốt nhất → nộp BTC 1 lượt. *Đo*: so `31.908` (exp_0018) / `32.798` (exp_0022).
- [ ] **3.3** Entity masking A/B `p=0/0.1/0.3` trên mốc tốt nhất. *Đo*: `text_score` + FP.
- [ ] **3.4** (tuỳ) masking theo type. *Đo*: như trên, tách theo type.

### Phase 4 — Nhánh rủi ro (chỉ khi Phase 3 xong)

- [ ] **4.1a** Trích 4 tầng pattern từ test → `data/patterns/` (skeleton, kiểu dòng, 724 khung, thống kê nhiễu).
      *Đo*: số khung sau lọc; review tay top-50.
- [ ] **4.1b** Generator điền slot từ khung + entity KB. *Đo*: LCS/n-gram gate pass 100%.
- [ ] **4.1c** A/B transductive vs control cùng số mẫu. *Đo*: `text_score` dev + BTC.
- [ ] **4.1d** Canh lại tỉ lệ prose (hiện ~32% entity vs test chỉ **2.1%** dòng văn xuôi dài).
      *Đo*: phân bố kiểu dòng synthetic vs test.
- [ ] **4.2** SapBERT-sweep thay lexicon-sweep (§6.2). *Đo*: entity bắt thêm, độ chính xác.
- [ ] **4.3** Tách holdout khỏi dev (§6.3).

---

## 8. Bảng theo dõi (điền dần)

| # | Thay đổi | dev text | dev assert | dev cand | BTC final | Kết luận |
|---|---|---|---|---|---|---|
| — | *nền: exp_0022* | 0.246* | — | — | **32.79790** | best hiện tại |
| 1.1+1.2 | sửa biên hậu xử lý | | | | | |
| 2.x | synthetic v5 (1.000) | | | | | |
| 3.1 | learning curve tốt nhất | | | | | |
| 3.3 | + entity masking | | | | | |
| 4.1 | + paraphrase | | | | | |

\* điền lại bằng `scripts/rescore_all.py` sau mỗi thay đổi.

---

## 9. Nhắc lại các bẫy đo lường đã trả giá

1. **Đổi span → dev xếp hạng candidate SAI.** Chỉ `text_score` so trực tiếp được (không có cơ chế
   abstain). Với candidate phải **bóc tách numerator**.
2. **Cùng span nhưng abstain rate không đổi → dev mù với hiệu ứng nhỏ** (bài học exp_0018).
3. **Không chỉnh metric theo độ khớp tuyệt đối với BTC** — chỉ theo xếp hạng (bài học exp_0012).
4. **val F1 trên synthetic là vô nghĩa** (cùng phân phối train). Thước thật chỉ có dev + BTC.
5. **Dev gold thiếu nhãn → thưởng cho over-predict.** Nhớ khi đọc mọi số dev.
