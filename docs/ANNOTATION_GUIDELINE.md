# ANNOTATION_GUIDELINE — Quy ước nhãn cho 5 type khái niệm y tế

> Contract dùng chung cho: (1) prompt sinh synthetic, (2) verifier xác định biên trong pipeline
> sinh data ([SYNTHETIC_V5_PLAN.md](SYNTHETIC_V5_PLAN.md)), (3) adjudication `data/labeled/`,
> (4) hậu xử lý NER ([TRAINING_WORKFLOW_PLAN.md](TRAINING_WORKFLOW_PLAN.md) §A1-A3).
>
> **Nguồn chuẩn khi có mâu thuẫn, theo thứ tự ưu tiên:**
> 1. Ví dụ chính thức trong `TASK/de_bai.md` + `TASK/de_bai_chi_tiet.md` (2 ví dụ duy nhất BTC cho).
> 2. Định nghĩa vận hành trong guideline VietBioNER (LREC 2022) — dùng khi đề không nói rõ.
> 3. Bằng chứng đo được trên `data/labeled/ground_truth/` (15 file, đã audit — xem §5).
> 4. Khi cả 3 đều im lặng: ghi rõ "CHƯA CHẮC", không đoán, adjudicate sau.
>
> Mọi rule ở đây có trích dẫn nguồn — không viết theo trực giác.

---

## 0. Hai ví dụ chính thức (trích nguyên văn, dùng làm bằng chứng xuyên suốt)

**Ví dụ 1** (`de_bai.md`), input:
> *"...ho đờm xanh, tức ngực, đau thượng vị, ợ hơi, được chẩn đoán mắc bệnh trào ngược dạ dày - thực
> quản. Bệnh nhân có tiền sử sử dụng Chlorpheniramine 0.4 MG/ML, Capsaicin 0.38 MG/ML, đã tiến hành
> tổng phân tích tế bào máu bằng máy lazer (tbm): WBC:14,43; NEUT% (Tỷ lệ % bạch cầu trung
> tính):76,4; LYPH% (Tỷ lệ bạch cầu lympho):12,8;"*

Output:
```
CHẨN_ĐOÁN : "bệnh trào ngược dạ dày - thực quản"
TRIỆU_CHỨNG : "ho đờm xanh", "tức ngực", "đau thượng vị", "ợ hơi"
TÊN_XÉT_NGHIỆM : "TWBC"⚠, "NEUT% (Tỷ lệ % bạch cầu trung tính)", "LYPH% (Tỷ lệ bạch cầu lympho)"
KẾT_QUẢ_XÉT_NGHIỆM : "14,43", "76,4", "12,8"
THUỐC : "Chlorpheniramine 0.4 MG/ML", "Capsaicin 0.38 MG/ML" ; assertion: "isHistorical"
```

**Ví dụ 2** (`de_bai_chi_tiet.md`), input:
> *"...1. amlodipine 10 mg po daily 2. aspirin 81 mg po daily ... 4. guaifenesin ml po q6h:prn
> điều trị ho ..."*

Output: `"amlodipine 10 mg po daily"`, `"aspirin 81 mg po daily"`, `"guaifenesin ml po q6h:prn"` — mỗi
span THUỐC gồm **tên + liều + đường dùng + tần suất**, tách khỏi cụm `"điều trị ho"` (đó là
`TRIỆU_CHỨNG` riêng).

⚠️ **Bất thường đã ghi nhận, KHÔNG áp dụng**: output ví dụ 1 ghi `"TWBC"` nhưng input chỉ có
`"WBC"` — không khớp substring (vi phạm invariant `raw[s:e]==text`). Gần như chắc chắn là lỗi
đánh máy trong tài liệu đề. Quy tắc vận hành: **span luôn phải là substring nguyên văn của raw**,
không bao giờ thêm ký tự không có trong input.

---

## 1. TRIỆU_CHỨNG (Symptom)

### 1.1. Phạm vi ngữ nghĩa
Biểu hiện thể chất/hành vi bất thường mà **bệnh nhân trực tiếp trải qua, quan sát, hoặc mô tả
được** — là *dấu hiệu* của quá trình bệnh lý, không phải bản thân bệnh lý đó.

> *Nguồn: VietBioNER guideline §4.2 — "Altered physical appearance or behaviour as a probable
> result of injury and/or underlying pathological process, and thus a sign of the disease process,
> rather than disease or illness in itself. Only symptoms that could be experienced, observed, and
> described by a patient directly."*

### 1.2. Bao gồm
- Triệu chứng đơn: `"tức ngực"`, `"ợ hơi"`, `"vỡ ối"` (ví dụ 1 + dev gold).
- **Cụm mô tả tính chất/đặc điểm gắn liền, không có dấu phẩy/động từ chen giữa**:
  `"ho đờm xanh"` (ví dụ 1 — màu đờm là đặc điểm định danh triệu chứng, không phải mệnh đề riêng),
  `"đau đầu dữ dội"`, `"mệt mỏi toàn thân"`, `"nghẹt mũi nhiều hơn"` (dev gold, đã audit §5.2).
- Có thể là tiếng Anh xen lẫn (code-switch): `"nausea"`, `"dyspnea"`.

### 1.3. Loại trừ
- **Bản thân bệnh/chẩn đoán** → tag `CHẨN_ĐOÁN`, không tag `TRIỆU_CHỨNG`.
- **Động từ dẫn/framing** (`cảm thấy`, `bị`, `có`, `xuất hiện`) — **KHÔNG nằm trong span**.
  *Bằng chứng*: audit dev gold phát hiện `'cảm thấy khó chịu chung'` sai — phải là
  `'khó chịu chung'` (đã sửa, xem §5.2).
- Mệnh đề mô tả diễn biến có **động từ/dấu phẩy tách biệt**: `"ho, nhiều hơn trước"` → chỉ tag
  `"ho"`, phần sau là mô tả diễn biến riêng (xem quy tắc biên chung §4).

### 1.4. Quy tắc biên
**Span = cụm danh từ tối đa liền mạch** (maximal NP), dừng lại khi gặp dấu phẩy, liên từ, hoặc
động từ mới. Bổ ngữ tính chất/mức độ **gắn trực tiếp không dấu phẩy** thì giữ trong span (`"đờm
xanh"`, `"dữ dội"`, `"toàn thân"`); bổ ngữ tách bằng dấu phẩy thì không.

### 1.5. Nhầm lẫn khó: TRIỆU_CHỨNG vs CHẨN_ĐOÁN
Đây là ranh giới gây lỗi sai-type nhiều nhất (đo được 4% trên dev, bị **phạt kép** theo đề).
- **CHẨN_ĐOÁN** = kết luận/tên bệnh do bác sĩ đưa ra, thường theo sau cue `"chẩn đoán"`,
  `"mắc bệnh"`, hoặc là danh từ bệnh lý có mã ICD-10 tra được.
- **TRIỆU_CHỨNG** = hiện tượng bệnh nhân tự cảm nhận được, KHÔNG tự nó là một bệnh.
- Test nhanh: *"Bệnh nhân có tự mô tả/cảm nhận được cái này không, hay đây là kết luận chuyên môn
  của bác sĩ?"* — VietBioNER ghi rõ: *"exclude diseases or illness as they have to be annotated as
  another category"*.
- Ca biên (CHƯA CHẮC, cần adjudicate khi gặp): `"tăng huyết áp"` — là chẩn đoán khi đứng độc lập
  làm kết luận, nhưng có thể coi như mô tả trạng thái khi xuất hiện trong danh sách triệu chứng.
  Ưu tiên theo **section/ngữ cảnh câu**, không theo tên cụm.

---

## 2. CHẨN_ĐOÁN (Diagnosis)

### 2.1. Phạm vi ngữ nghĩa
Tên bệnh/tình trạng bệnh lý là **kết luận chuyên môn**, ánh xạ được sang mã ICD-10.

> *Nguồn: VietBioNER §4.1 — "All diseases, illness, inflammation, or disorder conditions related
> to human". Annotator có thể tra ICD-10 để xác nhận.*

### 2.2. Bao gồm
- `"bệnh trào ngược dạ dày - thực quản"` (ví dụ 1) — giữ nguyên dấu `-` nội bộ.
- Bệnh mạn tính trong mục tiền sử: `"Bệnh thận đa nang"`, `"tăng huyết áp"`.
- Có thể ánh xạ **nhiều mã ICD** cho 1 span (ví dụ 1: `K21.0` + `K21.9`) — đây là thuộc tính của
  `candidates`, không ảnh hưởng span.

### 2.3. Loại trừ
- Triệu chứng đơn lẻ chưa có kết luận chẩn đoán → `TRIỆU_CHỨNG` (xem §1.5).
- Cue dẫn (`"được chẩn đoán mắc bệnh"`, `"chẩn đoán:"`) **không nằm trong span** — chỉ span tên
  bệnh sau cue.

### 2.4. Quy tắc biên
Giữ nguyên cụm danh từ y khoa đầy đủ kể cả có dấu `-`/`,` nội tại là một phần tên bệnh chính thức
(`"trào ngược dạ dày - thực quản"`). Dừng ở dấu phẩy đánh dấu liệt kê nhiều bệnh riêng biệt
(`"tăng huyết áp, đái tháo đường"` → 2 span).

---

## 3. THUỐC (Drug)

### 3.1. Phạm vi ngữ nghĩa
Tên thuốc bệnh nhân dùng/từng dùng, ánh xạ được sang RxNorm.

### 3.2. Quy tắc biên — ĐÃ KIỂM CHỨNG BẰNG 2 VÍ DỤ CHÍNH THỨC + AUDIT DEV GOLD

**Quy tắc**: span = tên thuốc + **mọi token liều/đường dùng/tần suất nối liền ngay sau tên,
KHÔNG có dấu phẩy, dấu hai chấm, hoặc động từ chen giữa**.

- Ví dụ 1: `"Chlorpheniramine 0.4 MG/ML"` — chỉ có liều (đường dùng không xuất hiện trong câu gốc
  nên không có gì để gộp thêm).
- Ví dụ 2: `"amlodipine 10 mg po daily"` — có cả liều + đường dùng + tần suất, nối liền không dấu
  phẩy → gộp hết.
- **KHÔNG gộp qua dấu hai chấm** kiểu `nhãn: mô_tả`: `"Torsemide: uống 1 viên/ngày..."` → chỉ tag
  `"Torsemide"`, phần sau dấu `:` là câu mô tả cách dùng riêng, không phải cụm liều gọn.
- **KHÔNG gộp nội dung trong ngoặc có động từ** mô tả sự kiện: `"prograf (dose decreased from
  5mg bid to 1mg bid)"` → chỉ tag `"prograf"`. Ngoặc chứa động từ (`decreased`, `đang dùng`) là
  narrative, không phải dose specifier gọn.
- **CÓ gộp** khi đường dùng/tần suất nối liền không qua dấu phẩy/động từ:
  `"heparin truyền tĩnh mạch liên tục"` (audit dev gold phát hiện thiếu, đã sửa — xem §5.1).

**Bài học**: đừng đo "% span có liều" làm chỉ báo đúng/sai — con số đó phụ thuộc việc *câu gốc
có đặt liều sát tên thuốc hay không*, không phải lỗi annotator. Áp quy tắc adjacency ở trên cho
từng ca cụ thể.

### 3.3. Loại trừ
- Hoạt chất xuất hiện với vai trò **xét nghiệm** (creatinine, troponin) → `TÊN_XÉT_NGHIỆM`, không
  phải `THUỐC` (đã có trong `_LAB_KW`/`_looks_drug` của `src/extraction/extractor.py`).

---

## 4. TÊN_XÉT_NGHIỆM & KẾT_QUẢ_XÉT_NGHIỆM

### 4.1. Bằng chứng từ ví dụ 1
```
"NEUT% (Tỷ lệ % bạch cầu trung tính):76,4"
   └──────────── TÊN_XÉT_NGHIỆM ────────────┘  └ KẾT_QUẢ_XÉT_NGHIỆM ┘
```
- `TÊN_XÉT_NGHIỆM` **gồm cả phần giải thích trong ngoặc** khi nó là một phần tên hiển thị của xét
  nghiệm (không phải narrative như trường hợp THUỐC ở §3.2 — phân biệt: đây không có động từ).
- `KẾT_QUẢ_XÉT_NGHIỆM` **chỉ là giá trị số** (`"76,4"`), không gồm dấu hai chấm hay đơn vị đứng
  tách biệt trước nó.
- Dấu hai chấm `:` giữa tên và giá trị **không thuộc span nào cả**.

### 4.2. Loại trừ
`KẾT_QUẢ_XÉT_NGHIỆM` không áp cho giá trị định tính không phải số/chỉ số đo lường trực tiếp (vd
mô tả bằng lời `"bình thường"`, `"không ghi nhận bất thường"` — các trường hợp này CHƯA CHẮC,
xem case study `notebooks/`/dev gold trước khi quyết).

---

## 5. Nhật ký sửa gold (2026, sau audit)

> Audit thực hiện bằng cách đối chiếu **toàn bộ 20 span THUỐC** và **8 span TRIỆU_CHỨNG có bổ
> ngữ** trong `data/labeled/ground_truth/` với quy tắc adjacency ở §3.2/§1.4. Kết quả: **19/20
> THUỐC đã đúng sẵn**, **8/8 TRIỆU_CHỨNG bổ ngữ đã đúng sẵn** — rút lại nhận định trước đó rằng
> gold "lệch hẳn convention đề" (số liệu thô 15% có liều gây hiểu lầm; nguyên nhân thật là phần
> lớn thuốc trong text không có liều nằm sát, không phải annotator bỏ sót).

| # | File | Trước | Sau | Lý do |
|---|---|---|---|---|
| 1 | 91.json | `"heparin"` | `"heparin truyền tĩnh mạch liên tục"` | Đường dùng+tần suất nối liền không dấu phẩy/động từ (§3.2) |
| 2 | 51.json | `"cảm thấy khó chịu chung"` | `"khó chịu chung"` | Loại động từ dẫn `"cảm thấy"` (§1.3) |

**Phát hiện phụ (chưa sửa, ghi nhận riêng)**: `50.json` — câu `"...chuyển sang sử dụng
azithromycin.Bệnh nhân đã dùng prednisone 40 mg..."` có `"prednisone 40 mg"` **không được gán
nhãn** ở lần xuất hiện thứ 2 trong file. Đây là vấn đề **completeness** (thiếu occurrence), khác
với vấn đề **boundary** đang sửa ở đây — thuộc phạm vi tổng rà soát occurrence đầy đủ
(xem [IDEAS.md](IDEAS.md) "Hoàn thiện dev gold"), không sửa trong đợt này để tránh mở rộng phạm vi.

---

## 6. Quy tắc biên chung (cross-type, dùng cho verifier)

Tổng hợp từ §1-§3, áp dụng máy được:

```
GIỮ trong span nếu phần mở rộng:
  - nối liền vào span hiện tại KHÔNG qua dấu phẩy/hai chấm
  - KHÔNG chứa động từ chia (decreased, đang dùng, giảm liều...)
  - là bổ ngữ tính chất/liều/đường dùng/tần suất gắn trực tiếp vào danh từ đầu

DỪNG span khi gặp:
  - dấu phẩy đánh dấu liệt kê / mệnh đề mới
  - dấu hai chấm (nhãn: giá trị — trừ khi bản thân là ranh giới TÊN_XN/KẾT_QUẢ_XN, xem §4.1)
  - động từ chia mới (trừ trường hợp §1.3 loại verb dẫn khỏi ĐẦU span, không phải giữa)
  - dấu ngoặc chứa động từ mô tả sự kiện (not liều gọn)
```

Dùng cho:
- `scripts/diagnose_boundary.py` — phân loại lỗi sai-biên theo quy tắc nào bị vi phạm.
- Verifier trong `SYNTHETIC_V5_PLAN.md` §IDEA 3 — kiểm tra span synthetic sinh ra tuân quy tắc.
- Hậu xử lý NER (`TRAINING_WORKFLOW_PLAN.md` §A2/A3) — cụ thể hoá bug cần sửa (không vươn qua
  ngoặc có động từ; nuốt qua dấu chấm thập phân là bug kỹ thuật riêng, không liên quan rule này).
