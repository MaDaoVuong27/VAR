# TRAINING WORKFLOW — Kế hoạch hoàn chỉnh cho 3 khối model

> Kế hoạch training/architecture cho toàn pipeline, tổng hợp ý tưởng đã phản biện từ
> **JMIR 2025** (synthetic + LLM annotation), **OpenBioNER v1/v2** (description-conditioned
> cross-encoder, entity masking, curriculum), **VietBioNER** (guideline tiếng Việt), cùng mọi
> phép đo nội bộ.
>
> Đi kèm: [SYNTHETIC_V5_PLAN.md](SYNTHETIC_V5_PLAN.md) (dữ liệu train), [IDEAS.md](IDEAS.md)
> (chiến lược tổng), [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md) (kết quả thật).

---

## 0. TL;DR

**Câu hỏi lớn nhất — description lấy từ đâu? Trả lời: KHÔNG cần LLM cho bất kỳ description nào.**

| Loại description | Số lượng | Nguồn | Vì sao không dùng LLM |
|---|---|---|---|
| **Type description** (5 type) | 5 | **Viết tay** từ `TASK/de_bai_chi_tiet.md` + guideline VietBioNER | Chỉ 5 cái. Viết tay chính xác hơn, và đây là *contract* của cả hệ thống — không được để LLM bịa. |
| **Code description** (ICD-10) | 15.844 | **Rule thuần từ CSV** — đã có sẵn 100% | KB đã chứa phân cấp 3 tầng + tên VN/EN + đồng nghĩa. LLM chỉ thêm nhiễu. |
| **Code description** (RxNorm) | 229.134 | **Rule thuần từ TTY** | 31% rxcui có nhiều TTY (SBD/SY/PSN/TMSY) → đa chiều sẵn. |

→ Toàn bộ description **xác định, tái lập bit-exact, offline, 0 tham số, 0 rủi ro hallucination**.
Đây là lợi thế lớn so với paper (họ phải dùng LLaMA-3.1-8B sinh description vì ontology của họ
không có sẵn trường mô tả).

**Đòn bẩy lớn nhất còn lại**: khối **candidate** (`23.47`, weight `0.4`). Và kiến trúc
OpenBioNER mà bạn thích — cross-encoder + description — **áp đúng vào khối này**, không phải NER.

---

## 1. Ta đang ở đâu — phân rã điểm

Best thật: **exp_0022 = 32.79790** (`WER 61.3095 · J_assertion 39.3464 · J_candidates 23.4669`).

| khối | điểm | weight | đóng góp | trần còn lại (nếu lên 100) |
|---|---|---|---|---|
| text | 38.69 | 0.3 | 11.61 | +18.4 |
| assert | 39.35 | 0.3 | 11.80 | +18.2 |
| **candidate** | **23.47** | **0.4** | **9.39** | **+30.6** ⭐ |

**Candidate vừa thấp nhất vừa nặng nhất.** Mọi thứ khác là thứ yếu.

Phân rã lỗi NER (đo trên exp_0022 vs dev gold, 162 concept):

| loại | số | ghi chú |
|---|---|---|
| ✅ exact (đúng type + đúng 2 biên) | 95 (59%) | |
| ~ đúng type, **sai biên** | 31 (19%) | **25% số ca bắt đúng type** — sửa được, không cần recall |
| ✗ overlap nhưng **sai type** | 7 (4%) | BTC **phạt kép** |
| ∅ miss hoàn toàn | 29 (18%) | lỗi recall |

---

## 2. Kiến trúc OpenBioNER — áp vào đâu là ĐÚNG

### 2.1. Nhận diện cốt lõi

```
OpenBioNER :  [CLS] text     [SEP] description(TYPE) [SEP]  → cross-encoder → score/token
Reranker ta :  [CLS] mention  [SEP] code_name         [SEP]  → cross-encoder → score
```

**Cùng một công thức.** Khác biệt: họ phân biệt giữa **5 type**, ta phân biệt giữa **hàng nghìn code**.

Điều đó có nghĩa: OpenBioNER là **bằng chứng độc lập rằng cross-encoder + mô tả ngữ nghĩa thắng
cross-encoder + tên trần**. Và reranker của ta **đang cho ăn tên trần** — xem `reranker.py:46-52`:

```python
pairs = [[query, p] for p in passages]      # query = mention THUẦN, p = code_name THUẦN
enc = tok(pairs, ..., max_length=64)        # 64 token — không đủ chỗ cho context/description
```

→ **Đây là chỗ áp OpenBioNER cho lợi ích cao nhất.**

### 2.2. Vì sao KHÔNG áp description-conditioning cho NER

1. **Ta ở chế độ full-data**: paper v1 §7.1 — lợi ích của description-pretraining là `+35.6 F1`
   ở 100 mẫu nhưng chỉ `+0.2` ở full data. Ta có ~23k entity.
2. **Chi phí ×6**: mỗi window phải encode lại cho từng type + NEG.
3. **Checkpoint của họ là English BioBERT**, 377 description tiếng Anh, multilingual là future work.
4. **Provenance**: weights của họ chưng cất từ GPT-3.5 silver labels + Qwen2.5-32B judge → rủi ro
   review khi nộp. *Học recipe thì sạch; lấy weights thì không.*

→ Với NER, ta lấy **3 kỹ thuật TRAINING** của họ (§3), không lấy kiến trúc.

---

## 3. MODULE A — NER (text 38.69, weight 0.3)

### A1. Sửa lỗi biên hậu xử lý ⭐ rẻ nhất, làm trước

- **Vấn đề đo được**: 25% span đúng type nhưng sai biên. Bốn kiểu:
  ```
  cắt giữa số : '5.8'→'8.'   '0.10'→'10'   '6.3'→'3, mẫu không tan máu'
  nuốt ngoặc  : 'prograf' → 'prograf (dose decreased from 5mg bid to '
  cắt cụt     : 'buồn nôn và nôn' → 'buồn nôn'
  mất đầu     : 'rối loạn lo âu' → 'âu'
  ```
- **Cách làm**: `_snap_word` bảo vệ `\d+[.,]\d+`; port `_trim_drug()` từ rule extractor sang
  `ner_extractor`.
- **Đo**: `diagnose_boundary.py` — nhóm "cắt giữa số" phải về ~0.
- **Rủi ro**: thấp, không đụng model.
- ⚠️ Đổi span → **dev xếp hạng candidate sai**; chỉ so `text_score`.

### A2. Entity masking (OpenBioNER)

- **Vấn đề**: model học thuộc canonical name + template slot (val F1 0.9998 = vô nghĩa).
- **Cách làm**: mask toàn bộ mention → `[MASK]` với xác suất `p` lúc train. A/B `p = 0 / 0.1 / 0.3`.
- **Đo**: `text_score` dev; lỗi trên surface form hiếm; FP ở ngữ cảnh giống template.
- **Rủi ro**: **KHÔNG copy `p=0.5`** của paper (họ chỉ dùng ở refinement stage).
  `KẾT_QUẢ_XÉT_NGHIỆM` (số+đơn vị) và `THUỐC` phụ thuộc mạnh surface form → vòng 2 mới thử
  **mask theo type** (cao cho CHẨN_ĐOÁN/TRIỆU_CHỨNG, thấp cho 2 type kia).

### A3. Curriculum 2 tầng (BroadScan → BioRefine)

- **Cách làm**: Stage 1 train trên toàn bộ synthetic (coverage) → Stage 2 continue-train ngắn
  (1–2 epoch) trên subset đã audit sạch, cân bằng hard-confusion.
- **Đo**: exact-span dev; so với chỉ-stage-1.
- **Rủi ro**: paper **không có ablation sạch** tách riêng lợi ích BioRefine (v2 đổi nhiều thứ cùng
  lúc: `+8.1 F1` là tổng của recipe + description selection + benchmark protocol).
  → đây là **giả thuyết**, phải A/B riêng, không bật masking mới trong cùng experiment.

### A4. Ensemble XLM-R-large + PhoBERT-base-v2 🆕

**Bằng chứng** — benchmark NER y tế tiếng Việt độc lập (VietMedNER, NAACL 2025, Table 3):

| model | params | P | R | **F1** |
|---|---|---|---|---|
| **XLM-R_large** (ta đang dùng) | 550M | **0.71** | 0.77 | **0.74** |
| **PhoBERT_base-v2** | 135M | 0.68 | **0.79** | **0.74** |
| PhoBERT_large | 370M | 0.69 | 0.77 | 0.73 |
| XLM-R_base | 270M | 0.64 | 0.73 | 0.69 |
| ViT5_base / BARTpho / mBART-50 | 310–611M | 0.64 | 0.66–0.74 | 0.65–0.69 |
| ViDeBERTa_base | 86M | 0.50 | 0.41 | 0.45 |

Hai kết luận:
1. **Đổi base model KHÔNG phải đòn bẩy** — XLM-R-large đã là tốt nhất bảng. Đây là lý do
   references cho NER ít ý tưởng hơn candidate: NER của ta đã gần trần kiến trúc.
2. **PhoBERT-base-v2 hoà điểm nhưng lệch hướng**: thiên **recall** (0.79 vs 0.77) trong khi
   XLM-R thiên **precision** (0.71 vs 0.68) → **bổ trợ nhau**, đúng ý tưởng ensemble ở
   [IDEAS_1.md](IDEAS_1.md) §4. Chỉ tốn thêm **135M** (tổng 1.819B/9B, vẫn dư 7.2B).

**Cách làm** (2 biến thể, đo riêng):
- `A4-a` **union + trọng tài theo conf**: gộp span 2 model, span chồng lấn thì lấy conf cao hơn.
  Thiên recall → hợp nếu chẩn đoán cho thấy "miss 18%" là nút thắt.
- `A4-b` **intersection**: chỉ giữ span cả 2 model đồng ý. Thiên precision → hợp với bài học
  `min_conf 0.95 > 0.6` (precision > recall trên BTC).

**Rủi ro phải kiểm trước khi đầu tư**:
- ⚠️ PhoBERT là **monolingual + cần word-segmentation** (VnCoreNLP), trong khi text của ta
  **61% file có code-switch** với tên thuốc/xét nghiệm tiếng Anh. Data VietMedNER là lời nói
  phiên âm — ít code-switch hơn nhiều. → **con số hoà 0.74 có thể không giữ trên dữ liệu của ta.**
- **Gate**: train PhoBERT-base-v2 đơn lẻ trên cùng synthetic trước; nếu `text_score` dev thua
  XLM-R-large quá 15% thì **bỏ hướng ensemble**, không làm tiếp.
- Word-segmentation làm **đổi offset** → phải map ngược về raw. Rủi ro kỹ thuật thật, phải test
  invariant `raw[s:e] == text`.

**Đo**: `text_score` dev (so trực tiếp được); tách riêng precision/recall theo type.

### A5. Ngưỡng theo type (calibration)

- **Vấn đề**: đang dùng **một** `min_conf=0.95` chung cho 5 type có độ khó rất khác nhau.
  Paper v2 đo được base model overconfident, Brier tệ hơn 40–50% trên type hiếm.
- **Cách làm**: precision-coverage curve riêng từng type → ngưỡng riêng.
- **Rủi ro**: dev gold thiếu nhãn → thưởng over-predict. Phải xem numerator, không xem tổng.
  Đã quét `min_conf` 0.80–0.99 trên nền classifier: **phẳng** → tín hiệu yếu, để sau.

---

## 4. MODULE B — Assertion (39.35, weight 0.3)

### B1. Type description cho assertion

- **Cách làm**: đưa mô tả `isNegated` / `isHistorical` / `isFamily` vào input classifier
  (`[CLS] context [SEP] mô tả assertion [SEP]`), hoặc dùng làm prompt cho synthetic generator.
- ⚠️ **Assertion là MULTI-LABEL** (một concept có thể vừa historical vừa negated), trong khi
  OpenBioNER dùng softmax loại trừ nhau → **không port nguyên kiến trúc**, chỉ mượn ý description.
- **Rủi ro**: classifier hiện đã thắng rule **+2.97** trên BTC. Không đập đi xây lại khi chưa có
  bằng chứng — paper không có experiment assertion nào.

### B2. Nhãn assertion sạch từ synthetic v5

- **Vấn đề**: nhãn assertion prose nhiễu (`isNegated` khớp ~59%).
- **Cách làm**: verifier xác định trong SYNTHETIC_V5 §IDEA 3 → chỉ giữ mẫu khớp.
- **Đo**: khớp 59% → mục tiêu >90%; rồi `J_assertion` BTC.
- **Đây là đường vào chính cho assert**, không phải đổi kiến trúc.

---

## 5. MODULE C — Candidate ⭐ ĐÒN BẨY LỚN NHẤT (23.47, weight 0.4)

### C1. Code description dựng bằng RULE từ KB ⭐⭐ việc quan trọng nhất

**Độ phủ đã đo trên `icd10_vn.csv` (15.844 dòng, 29 cột):**

| trường | phủ |
|---|---|
| `ten_benh_vi` / `disease_name_en` | **100%** |
| `ten_nhom_3ky_tu_vi` (nhóm 3 ký tự) | **100%** |
| `ten_khoi_vi` (khối) | **100%** |
| `ten_chuong_vi` (chương) | **100%** |
| `huong_dan_bo_sung_vi` (**tên gọi khác/đồng nghĩa**) | 40.2% |
| cờ ngữ nghĩa (`chỉ_nữ`, `chỉ_nam`, `không_dùng_bệnh_chính`…) | 2.427 / 933 / 144… |

**Ví dụ dựng bằng rule thuần cho `A00.0`:**
```
"Bệnh tả do vi khuẩn Vibrio cholerae 01, típ sinh học cholerae (còn gọi: Bệnh tả cổ điển).
 Thuộc nhóm Bệnh tả, khối Bệnh truyền nhiễm đường ruột, chương Bệnh truyền nhiễm và ký sinh trùng.
 Tên tiếng Anh: Cholera due to Vibrio cholerae 01, biovar cholerae."
```

**RxNorm** (362.409 dòng, 229.134 rxcui): 31% rxcui có **>1 TTY** → dựng description đa chiều từ
`IN` (hoạt chất) / `BN` (brand) / `SCD` (clinical drug + liều + dạng) / `SY`,`PSN`,`TMSY` (đồng nghĩa):
```
rxcui 93252:
  SBD  : hydrochlorothiazide 50 MG / triamterene 75 MG Oral Tablet [Maxzide]
  SY   : Maxzide (triamterene 75 MG / HCTZ 50 MG) Oral Tablet
  PSN  : MAXZIDE 75 MG / 50 MG Oral Tablet
```

- **Đo**: % code dựng được description; độ dài trung bình; sau đó là điểm reranker.
- **Rủi ro**: description dài làm tăng recall nhưng **giảm precision** (paper v2 §description
  richness). → thử **nhiều mức richness** như paper, không mặc định dài nhất tốt nhất.

### C2. Đưa NGỮ CẢNH vào query của reranker

- **Vấn đề**: `reranker.py` hiện truyền `query = mention thuần`, `max_length=64`.
  Mất hết ngữ cảnh phân biệt (`"suy thận"` trong câu nói về mạn tính vs cấp tính → mã khác nhau).
- **Cách làm**: `query = mention + câu chứa nó`; `passage = code description (C1)`;
  nâng `max_length` 64 → 192/256.
- **Đo**: dev cand (span cố định → **dev tin được**, xem §8).
- **Rủi ro**: chậm hơn (chuỗi dài hơn). Đo latency.

### C3. Fine-tune reranker (KHÔNG phải fine-tune SapBERT)

- **Vì sao lần này khác 2 lần thất bại trước**: exp_0016/0017 fine-tune **SapBERT** chết vì
  contrastive loss **dịch chuyển toàn phổ similarity** → ngưỡng abstain 0.7 mất hiệu lực.
  **Cross-encoder reranker chỉ đổi THỨ TỰ trong tập đã qua ngưỡng** (đã verify: abstain rate
  22%=22% giữa exp_0013 và exp_0018) → **miễn nhiễm cấu trúc với chế độ hỏng đó**.
- **Dữ liệu train MIỄN PHÍ**: **211.890 cặp positive** (variant, variant) cùng mã từ chính KB
  (ICD 15.844 + RxNorm 196.046).
- **Hard negative**: mã **gần nghĩa nhưng khác thật** — lấy từ cùng `ma_nhom_3ky_tu` /
  cùng khối ICD, hoặc cùng ingredient khác liều ở RxNorm. **Không** lấy synonym cùng mã làm negative.
- ⚠️ **Rủi ro lớn nhất, phải nói rõ**: cặp KB là *canonical ↔ canonical*, còn query thật là
  *span lộn xộn từ NER*. Đúng khoảng cách miền đã giết exp_0016.
  **Giảm bằng**: sinh **biến thể nhiễu xác định** từ tên chuẩn (viết tắt, đảo trật tự từ, span cụt,
  bỏ dấu, thêm/bớt modifier) — mô phỏng đúng thứ NER thật sự trả ra. Không cần LLM.
- **Đo**: dev cand; **phải recalibrate ngưỡng abstain** sau khi phổ score đổi.

### C4. Dùng phân cấp ICD để chọn granularity

- **Cách làm**: khi mention mơ hồ, lùi về mã cha 3 ký tự (`ma_nhom_3ky_tu`) thay vì đoán mã con.
  Dùng cờ `flag_khong_dung_co_ma_cu_the_hon` (2.119 mã) để loại mã không nên dùng.
- **Đo**: dev cand + tỉ lệ abstain.
- **Ghi chú**: đây là "graph vừa đủ" mà IDEAS_2 §4 đã đề xuất, giờ có dữ liệu cụ thể.

---

## 6. MODULE D — Xuyên suốt

### D1. Artifact `docs/ANNOTATION_GUIDELINE.md` (5 type)

Cấu trúc 6 mục/type (học OpenBioNER §9.1) — dùng chung cho: prompt generator, verifier biên,
adjudication dev gold, và (nếu có) type-conditioned verifier.

**Nguồn chuẩn khi mâu thuẫn**: ví dụ trong `TASK/de_bai_chi_tiet.md`.
**Tham khảo**: guideline VietBioNER (LREC 2022) — có định nghĩa vận hành cho phân biệt
symptom/disease, đúng chỗ ta bị phạt kép:

> *Symptom: "Altered physical appearance or behaviour as a probable result of injury and/or
> underlying pathological process, and thus a sign of the disease process, **rather than disease
> or illness in itself**. Only symptoms that could be experienced, observed, and described by a
> patient directly."*

⚠️ VietBioNER **gộp** Symptom+Disease làm một type vì phân biệt chúng khó — vừa là cảnh báo, vừa
xác nhận 4% lỗi sai type của ta là vấn đề bản chất, không phải model kém.

### D2. Diagnostics `scripts/diagnose_boundary.py`

Báo cáo: exact / sai-biên-trái / sai-biên-phải / sai-type / miss / thừa, **tách theo type**.
Chạy TRƯỚC và SAU mọi thay đổi. Khoảng cách overlap-vs-exact là **chẩn đoán**, không phải thành tích.

### D3. Không dùng LLM ở inference (giữ ngân sách)

| khối | model | params |
|---|---|---|
| NER | XLM-R-large | 560M |
| Assertion | XLM-R-base | 278M |
| Retrieval | SapBERT | 278M |
| Reranker | BGE-v2-m3 | 568M |
| **tổng hiện tại** | | **1.684B / 9B** |

Dư **7.3B**. Qwen2.5-7B sinh synthetic **không cộng vào** (chạy lúc train, khác thời điểm).
Chỉ căng nếu đặt LLM vào inference (verification agent): `1.684 + 7.62 = 9.3B > 9B` →
lúc đó hạ reranker 568M → mMiniLM 118M, mua đúng 450M margin.

---

## 7. TODO — theo phase, mỗi task có ô điền điểm

### Phase A — Nền + sửa rẻ (không cần train lại)

| # | Task | dev text | dev assert | dev cand | BTC final | Kết luận |
|---|---|---|---|---|---|---|
| — | *nền exp_0022* | | | | **32.79790** | best hiện tại |
| A-1 | `diagnose_boundary.py` — dựng baseline chẩn đoán | — | — | — | — | |
| A-2 | Sửa `_snap_word` bảo vệ số thập phân | | | | | |
| A-3 | Port `_trim_drug()` sang ner_extractor | | | | | |
| A-4 | `ANNOTATION_GUIDELINE.md` (5 type) | — | — | — | — | |
| A-5 | Sửa dev gold theo guideline (20 THUỐC + 8 bổ ngữ) | — | — | — | — | gold nhất quán |

### Phase C — Candidate (đòn bẩy lớn nhất, ưu tiên cao nhất sau A)

| # | Task | dev cand | BTC cand | BTC final | Kết luận |
|---|---|---|---|---|---|
| C-1 | `build_code_descriptions.py` (rule từ KB) | — | — | — | % phủ, độ dài TB |
| C-2 | Reranker ăn description (giữ query=mention) | | | | |
| C-3 | Reranker ăn **mention+context** ↔ description | | | | |
| C-4 | Quét mức richness description (name / +đồng nghĩa / +phân cấp) | | | | |
| C-5 | Fine-tune reranker trên 211.890 cặp KB + hard-neg | | | | |
| C-6 | Recalibrate ngưỡng abstain sau C-5 | | | | |
| C-7 | ICD hierarchy chọn granularity + cờ loại mã | | | | |

### Phase B — Assertion

| # | Task | dev assert | BTC assert | BTC final | Kết luận |
|---|---|---|---|---|---|
| B-1 | Verifier assertion cho synthetic v5 | — | — | — | khớp 59%→>90% |
| B-2 | Train lại classifier trên nhãn đã verify | | | | |
| B-3 | (tuỳ) description-conditioned assertion | | | | |

### Phase A2 — NER training techniques (cần synthetic v5 xong)

| # | Task | dev text | BTC WER | BTC final | Kết luận |
|---|---|---|---|---|---|
| A-6 | Entity masking A/B `p=0/0.1/0.3` | | | | |
| A-7 | Masking theo type | | | | |
| A-8 | Curriculum 2 tầng (broad→refine) | | | | |
| A-9 | **Gate**: PhoBERT-base-v2 đơn lẻ vs XLM-R-large | | | | bỏ ensemble nếu thua >15% |
| A-10 | Ensemble `union + trọng tài conf` (A4-a) | | | | |
| A-11 | Ensemble `intersection` (A4-b) | | | | |
| A-12 | Ngưỡng theo type | | | | |

---

## 8. Quy tắc đánh giá — nhắc lại để không lặp sai lầm cũ

1. **Đổi span (NER/boundary/masking) → dev xếp hạng candidate SAI.** Chỉ `text_score` so trực
   tiếp được. Candidate phải **bóc tách numerator**.
2. **Giữ span, đổi matcher → dev tin được** (kiểm chứng 3/3 nhóm)… **trừ khi abstain rate không
   đổi**, lúc đó dev mù với hiệu ứng nhỏ (bài học exp_0018: dev báo sai hướng).
   → **Phase C hầu hết giữ span** ⇒ dev dùng được, nhưng C-5/C-6 đổi abstain ⇒ cần BTC.
3. **Không chỉnh metric theo độ khớp tuyệt đối với BTC** — chỉ theo xếp hạng (bài học exp_0012).
4. **val F1 trên synthetic vô nghĩa** (cùng phân phối train).
5. **Dev gold thiếu nhãn → thưởng over-predict.**
6. **Mỗi lượt nộp cho 3 phép đo** (`WER`, `J_assertion`, `J_candidates`), không phải 1. Ghi
   nguyên văn mọi chữ số.

---

## 9. Thứ tự khuyến nghị + lý do

1. **A-1 → A-5** (nền, rẻ, không train): dựng chẩn đoán + sửa 2 bug biên + chốt guideline.
   *Lý do*: A-2/A-3 có thể tăng `text` ngay mà không đụng model; guideline là contract cho mọi thứ sau.
2. **C-1 → C-4** (candidate, không train): description từ KB + đưa vào reranker.
   *Lý do*: **đòn bẩy 0.4 lớn nhất**, không cần train, dev đọc được (giữ span).
3. **B-1 → B-2** (assertion): cần synthetic v5.
4. **C-5 → C-7** (fine-tune reranker): đắt hơn, làm sau khi C-2/C-3 chứng minh description có ích.
5. **A-6 → A-9** (NER training): cần synthetic v5 xong.

**Không làm**: port checkpoint OpenBioNER (English BioBERT, full-data regime, provenance GPT-3.5);
description-conditioning cho NER (chi phí ×6, lợi ích ~0 ở full-data); thay assertion classifier
đang thắng bằng kiến trúc softmax đơn nhãn.
