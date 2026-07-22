# DATA_PLAN — Làm sạch dữ liệu & Sinh synthetic data

> Kế hoạch dữ liệu dùng chung cho cả 3 hướng ([IDEAS_1](IDEAS_1.md)/[2](IDEAS_2.md)/[3](IDEAS_3.md)). **Đây là phần quyết định thành bại** của mọi hướng có học: ta chỉ có 100 sample và **không được train trên chúng** (là tập test BTC). Không có synthetic tốt → không fine-tune được gì.

---

## PHẦN 1 — Làm sạch dữ liệu (cleaning)

### Vấn đề (từ `EDA_FINDINGS.md` §2, đã kiểm chứng trên case study)
- **Token dính liền** (camel glue): `động mạchcho`, `tạiBệnh`, `giáckhó` (27/100 file).
- Thiếu dấu cách sau dấu câu; **token lặp**: `bình thườngbình thường`; **code-switch** VN-EN (61/100); markdown `**`; filler `N/A`.

### ⚠️ Ràng buộc VÀNG: offset phải giữ trên RAW gốc
Metric chấm `position` theo ký tự trên **input gốc chưa sửa**. Nếu clean làm đổi độ dài chuỗi → mọi offset lệch → hỏng text_score. Vì vậy **KHÔNG được nộp text đã clean**. Hai chiến lược:

1. **[Khuyến nghị] Model chạy trên RAW, clean chỉ để hỗ trợ matching**: NER/LLM đọc raw (chịu nhiễu — model học được điều này nếu synthetic có nhiễu tương tự); chỉ khi *so khớp candidate* mới normalize (tách glue, bỏ dấu...) trên bản copy, không đụng offset.
2. **Alignment map**: nếu buộc phải clean để model đọc, giữ mảng ánh xạ `offset_clean → offset_raw` để map ngược span về raw. Phức tạp, dễ sai — chỉ dùng nếu (1) không đủ.

### Các bước clean (chỉ áp cho bản matching, không cho output)
- Tách camel glue: chèn space giữa `[thường][HOA]` và giữa `[việt][ascii]` khi nghi dính.
- Gộp token lặp liền kề; chuẩn hoá khoảng trắng; bỏ `**`, `N/A`.
- **Quan trọng cho synthetic**: giữ LẠI các nhiễu này trong data train (xem Phần 2) để model **quen** với chúng — không "lau sạch" test bằng cách giả vờ test sạch.

---

## PHẦN 2 — Sinh Synthetic Data (cốt lõi)

> ### ⚠️ RÀNG BUỘC NỘP BÀI & LIÊM CHÍNH CHO SYNTHETIC (đọc trước khi làm)
> Top ~15 đội phải **nộp cả**: code pipeline (bao gồm **code sinh synthetic**) + **data đã dùng** + model weights + README. Hệ quả bắt buộc:
> 1. **Nộp KÈM file synthetic gốc** mà ta thực sự đã train. Khi BTC re-run, code sinh synthetic có yếu tố ngẫu nhiên (seed, sampling LLM) nên **không tái tạo y hệt** — vì vậy phải nộp bản synthetic gốc; code sinh chỉ để BTC **tham khảo cách làm** + hiểu quy trình, không phải để tái tạo bit-by-bit.
> 2. Vì code sinh synthetic **bị BTC review**, nó **cũng phải tuân luật**: chỉ dùng **model self-host ≤9B, KHÔNG API ngoài** (Claude/GPT/Gemini...). Không được dùng LLM mạnh ngoài để sinh data train — dù data train không phải output nộp bài, nhưng code lộ ra là dùng API ngoài → vi phạm tinh thần "self-host" và không tái tạo được.
> 3. Ghi rõ trong README: seed, model dùng để sinh, phiên bản KB — để quy trình minh bạch, tái lập ở mức quy trình.
>
> (Lưu ý phân biệt với ngân sách 9B của inference: model sinh synthetic chạy **lúc train, khác thời điểm** với inference nên không cộng dồn vào tổng 9B của pipeline nộp; nhưng bản thân nó vẫn phải là self-host ≤9B, không API ngoài.)

Triết lý user (đồng ý): **thử từ cơ bản → nâng cao, đo từng cái — biết đâu cơ bản đã đủ tốt**. Mục tiêu chính của bài là *model học được KHI NÀO một cụm là khái niệm y tế* (span + type) — nên đôi khi giữ **cấu trúc câu** quan trọng hơn tính đúng y học của nội dung.

> ### ⚠️ MÂU THUẪN NỘI BỘ CẦN CHỐT (ghi nhận 2026-07-15, CHƯA quyết)
> Mục "Nguồn nguyên liệu" ngay dưới **cho phép** *"nhại lại cấu trúc 100 sample thật để giữ phân phối test"*, trong khi mục §CHỐNG DATA LEAKAGE bên dưới **cấm** *"kể cả chỉ mượn cấu trúc câu"*. `CLAUDE.md` theo vế cấm. **Code hiện theo vế cho phép.**
>
> **Đo được** (2026-07-15): **34/75 chuỗi literal trong `generate.py` (45%)** và **115/169 trong `lexicons.py` (68%)** xuất hiện NGUYÊN VĂN trong 100 file test. Nhưng phải tách 2 loại:
> - **Trùng vô hại** (phần lớn `lexicons.py`): `"khó thở"`, `"đau bụng"`, `"công thức máu"` — là **sự thật về y học tiếng Việt**, corpus lâm sàng VN nào cũng có, sẽ trùng dù chưa từng mở file test. KHÔNG phải leakage.
> - **Dấu vân tay tập test** (`FILLER_LINES` trong `generate.py`): `"Vị trí: N/A"`, `"Tần suất: N/A"`, `"Tình trạng ngay trước khi nhập viện:"`, `"Các phát hiện chẩn đoán khác:"` — **không phải tiếng Việt lâm sàng phổ thông**, mà là giàn giáo riêng của generator tạo ra bộ test. Chỉ viết được nếu ĐÃ đọc file test. Đây mới là thứ §CHỐNG LEAKAGE nhắm tới.
>
> **Đánh giá**: KHÔNG phải gian lận theo đề (đề phát test input công khai **không nhãn** + *khuyến khích* tự tạo data train; 3 điều đề cấm — hard-code output / LLM ngoài sinh output / gán nhãn tay test — đều không phạm). Rủi ro thật là **overfit private test**, tức vấn đề **điểm số**, không phải liêm chính. → Cần chốt 1 luật duy nhất, hiện đang treo.

### Nguồn nguyên liệu
- **Template câu**: cấu trúc 100 sample thật (mục, bullet, câu văn xuôi) — nhại lại để giữ phân phối test. ⚠️ Xem callout mâu thuẫn ngay trên.
- **Danh mục entity**: tên bệnh (ICD-10 VN+EN), tên thuốc (RxNorm), + **lexicon triệu chứng / tên xét nghiệm / kết quả** tự gom (từ 100 sample + guideline).
- **Nguồn ngoài** (hợp lệ, đề khuyến khích tạo data train): MIMIC/i2b2/n2c2 (EN, dịch sang VN), VietMed-NER/ViMedNER.

> 🚫 **CHỐNG DATA LEAKAGE (đọc kỹ)**: "câu thật/câu mẫu" ở mọi cấp bên dưới = câu **do TA tự viết** (template) hoặc từ **corpus ngoài hợp lệ** (MIMIC/i2b2 dịch — KHÔNG phải data thi). **TUYỆT ĐỐI KHÔNG** lấy 100 file `data/raw/input/` (test BTC) làm câu gốc để thay entity, kể cả chỉ "mượn cấu trúc câu" — đó là leakage (model học phân phối test). Triển khai hiện tại (`src/synthetic/generate.py`) dùng template tự viết, KHÔNG đọc file test — giữ nguyên tắc này.

### Cấp 1 — Entity replacement (brute force, ý user) ⭐ làm trước
Lấy **câu template TỰ VIẾT** (mô phỏng văn phong lâm sàng, KHÔNG copy từ file test), thay các span khái niệm bằng entity khác **CÙNG TYPE** lấy từ danh mục KB:
- "Bệnh nhân có tiền sử **hen suyễn**" → "...tiền sử **tăng huyết áp** / **viêm dạ dày** / ...".
- Nhãn tự sinh **chính xác** vì ta biết vị trí + type + (map được mã từ KB). Assertion giữ theo cue câu.
- **Ưu**: rẻ, an toàn, nhãn chuẩn 100%, giữ cấu trúc + nhiễu (nếu chèn glue/code-switch). Dạy model "vị trí nào là entity". **Nhược**: đa dạng ngữ cảnh hạn chế (phụ thuộc số template tự viết).
- **Biến thể**: thay cùng type (giữ nhãn đúng) HOẶC thay tên bất kỳ + random assertion, chấp nhận sai lý thuyết, tăng đa dạng bề mặt. → **thử cả hai, đo.**

### Cấp 2 — Template + slot-filling
Viết template có slot (`Bệnh nhân {tiền_sử?} {DX}, được kê {DRUG} {liều}`) — **template do ta viết**, rồi điền slot ngẫu nhiên từ KB + bảng assertion. Sinh **cấu trúc mới**, kiểm soát phân phối type/assertion (cân bằng `isFamily` hiếm). *(Đây là cách `generate.py` hiện dùng.)*

### Cấp 3 — LLM sinh ghi chú (reverse từ code) — CHỈ self-host ≤9B ✅ ĐÃ TRIỂN KHAI: `src/synthetic/llm_prose.py`
> Qwen2.5-7B-Instruct 4-bit, chạy local qua `transformers`+`bitsandbytes` (**không** cần Ollama/systemd → BTC tái lập bằng `pip` thuần). Chọn entity TRƯỚC → LLM viết văn xuôi chứa nguyên văn → dò offset bằng tìm chuỗi; entity nào không tìm thấy thì **BỎ cả doc** (không đoán mò, nhãn luôn tuyệt đối đúng). Lệnh: `python -m src.synthetic.llm_prose --n 1500 --out data/synthetic/prose.jsonl`.

Cho trước danh sách (mã ICD/RxNorm + assertion), yêu cầu **LLM self-host ≤9B** (vd Qwen2.5-7B, đã có qua Ollama) viết đoạn ghi chú lâm sàng VN chứa chúng theo văn phong test (kể cả văn xuôi xen kẽ — đúng thứ baseline chết). Vì ta *chọn trước* entity nên **nhãn biết sẵn** (chỉ cần căn offset lại trong câu LLM sinh). Đa dạng cao nhất, mô phỏng được prose.
- ⚠️ **BẮT BUỘC self-host ≤9B, KHÔNG API ngoài** (xem callout đầu Phần 2). Không dùng Claude/GPT để sinh data train — code sinh bị BTC review, dùng API ngoài là vi phạm + không tái lập được. Model A100 của teammate chỉ để chạy nhanh hơn, vẫn phải là model self-host ≤9B.
- Nộp kèm file synthetic gốc do bước này sinh ra (LLM sampling không tái tạo y hệt).

### Cấp 4 — Kết hợp + weak-label review
Trộn cấp 1-3; dùng rule/pipeline hiện tại **weak-label** thêm rồi người review (chỉ cho DEV, không cho test). Bổ sung ca biên (type dễ nhầm, phủ định phức tạp).

### Đảm bảo phủ feature (bắt buộc)
Synthetic phải chứa cùng nhiễu với test: **token dính liền + code-switch** (spec ở `data/labeled/SELECTION.md`), câu văn xuôi xen kẽ (như sample 6/8), phủ định trong câu, `isFamily` hiếm. Nếu train trên data "sạch đẹp" thì model sẽ lại chết trên test bẩn.

#### Synthetic v3 (2026-07-15) — đã sửa 3 lỗi đo được của v2

| | v2 (cũ) | v3 | test thật |
|---|---|---|---|
| độ dài doc (median) | 560 ký tự | **1277** | **1229** |
| % doc có nhiễu glue *(detector của `notebooks/eda_features.py`)* | 16% *(toàn từ template lặp)* | **40%** | **27%** |
| mật độ entity | cố định 1/52 ký tự | **biến thiên** p10=32, median=49, p90=108 | *không biết* |

1. **`_maybe_glue()` là code chết** — được định nghĩa nhưng KHÔNG BAO GIỜ được gọi → v2 có **0%** nhiễu dính chữ do template sinh ra (16% đo được là PHRASE_REPEAT của template lặp, không phải glue). v3 thay bằng `_Noise` + `_sep()`, bật ~27% doc.
2. **Doc quá ngắn** (560 vs test 1229) → model chưa bao giờ thấy note dài lúc train. v3 sinh tới độ dài mục tiêu rút từ lognormal bám phân phối test.
3. **`t_filler` gắn bullet vào header** → sinh ra `"- 1. Tiền sử bệnh"` vô nghĩa. v3 tách `FILLER_HEADERS`, header không bao giờ có bullet.

⚠️ **Mật độ entity: KHÔNG có bằng chứng v2 "quá dày"** — `IDEAS.md` từng khẳng định vậy nhưng dựa trên dev gold **thiếu nhãn**. Số thật: dev gold cho **1 entity/150 ký tự** (chỉ là *cận dưới*), còn **ví dụ gốc của đề — nhãn THẬT của BTC — cho 1/28** (nhưng đó là danh sách thuốc = đậm đặc nhất). v2 ở 1/52 **nằm giữa hai mốc**. → v3 cho mật độ **biến thiên theo doc** để phủ cả dải, thay vì cược vào một giá trị ta không biết.

⚠️ **Bug train/inference lệch nhau (sửa 2026-07-15)**: `scripts/train_ner.py` tokenize bằng `truncation=True` **không có sliding window**, trong khi `ner_extractor.py` lúc inference thì CÓ. Với v2 (560 ký tự ≈ 180 token) hầu như vô hại, nhưng v3 (1277 ký tự ≈ 400 token > maxlen 256) sẽ **mất 45.7% nhãn** (đo trên 300 doc: giữ 5154/9499 → 9499/9499 sau khi sửa), và mất theo kiểu thiên lệch — chỉ giữ đầu document.

### ⚠️ Nguyên tắc tách feature giữa DEV và TRAIN (đã chốt)
Với 1 feature khó (vd văn xuôi xen kẽ — file baseline rỗng 6/8/25/93):
- **DEV chỉ cần 1-2 ca "canary"** để ĐO năng lực, giữ đúng **phân phối** của 100 test (4 file rỗng = 4% test → ~1-2/30 dev là vừa; nhồi cả 4 vào dev = over-represent, lệch ngược).
- **TRAIN (synthetic) mới là nơi đổ KHỐI LƯỢNG** ca prose để model HỌC — sinh nhiều câu văn xuôi xen kẽ, phủ định trong câu.
- ⚠️ **KHÔNG** dùng file test (kể cả file prose không vào dev) làm template/nguyên liệu synthetic — kể cả "mượn kiểu câu". Nếu cần bắt chước văn phong prose, **tự viết** template mô phỏng đặc điểm đó (câu dài xen kẽ, phủ định trong câu), không copy từ `data/raw/input/`.

## Thứ tự thực thi
1. Gom lexicon (triệu chứng/xét nghiệm/kết quả) + chuẩn hoá danh mục entity từ KB.
2. **Cấp 1** entity replacement → tập train NER v1 → fine-tune ([IDEAS_1](IDEAS_1.md)) → đo. (Kiểm chứng giả thuyết "cơ bản đã đủ".)
3. **Cấp 2/3** nếu cấp 1 chưa đủ đa dạng → đo delta.
4. Cân bằng class + ca biên (cấp 4).

## Nguồn tham khảo
- [LLM-Based Synthetic Data Generation for Clinical NER (2025)](https://link.springer.com/chapter/10.1007/978-3-032-05176-9_26) + [code](https://github.com/LIAAD/SDG_clinical_ner)
- [Structured LLM Augmentation for Clinical Information Extraction (2025)](https://pubmed.ncbi.nlm.nih.gov/40776002/)
- [Tổng hợp SDG bằng LLM (repo)](https://github.com/ahmad-alismail/LLM_based_Synthetic_Data_Generation)
