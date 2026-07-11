# EDA — Quan sát dữ liệu & định hướng phân tích

Ghi lại đặc điểm tập test 100 file (`data/raw/input/`) sau khi quan sát trực tiếp, cộng checklist EDA cần làm kỹ hơn bằng code. Đây là dữ liệu **không nhãn** — mọi nhận định về ground truth ở đây là suy luận từ đề bài + ví dụ, cần kiểm chứng khi gán nhãn `data/labeled/`.

Liên kết: [TASK_SPEC.md](TASK_SPEC.md) (đề bài/metric), [IDEAS.md](IDEAS.md) (lộ trình giải pháp dựa trên các quan sát này).

---

## 1. Nguồn gốc & cấu trúc dữ liệu

- Là **ghi chú lâm sàng tiếng Việt**, văn phong dịch máy/nửa dịch từ bệnh án tiếng Anh (kiểu MIMIC: discharge summary / history of present illness). Rất nhiều thuật ngữ, tên thuốc, cụm bệnh giữ nguyên tiếng Anh.
- Đa số file **bán cấu trúc** theo khung 3 mục lặp lại:
  1. `1. Tiền sử bệnh` (bệnh mạn tính, thuốc trước nhập viện, tiền sử phẫu thuật, yếu tố nguy cơ)
  2. `2. Bệnh sử hiện tại / Lịch sử bệnh hiện tại` (lý do nhập viện, triệu chứng hiện tại, diễn biến)
  3. `3. Đánh giá tại bệnh viện` (kết quả xét nghiệm, chẩn đoán hình ảnh, thủ thuật)
- Nội dung chủ yếu là **bullet list** (`-`, `*`, `+`) và cặp `nhãn: giá trị` ("Lý do nhập viện: ...").
- **Độ dài** (ký tự): min 182, max 5702, median ~1579. → độ dài chênh lệch lớn, cần xử lý được cả note ngắn 5 dòng lẫn note dài 140 dòng.

## 2. Nhiễu & thách thức tiền xử lý (rất quan trọng)

Đây là đặc điểm nổi bật nhất, ảnh hưởng trực tiếp tới NER và tính `position` (offset ký tự):

- **Token lặp dính liền**: `bình thườngbình thườngbình thường`, `đái tháo đườngđái tháo đường`, `bệnh sử hiện tạiBệnh nhân`, `klonopinclonidine`, `mltrong`, `giáckhó chịu`. Do lỗi ghép chuỗi khi tạo data.
- **Thiếu dấu cách** giữa từ/câu: `chuyển dạBệnh sử`, `81mg (asa81)`.
- **Code-switching Việt–Anh** ngay trong 1 file: `nausea`, `diarrhea`, `abdominal pain`, `taking 10 pills at a time`, `combivent nebs x3 every 20 minutes`.
- **Artifact markdown**: `**khó thở khi gắng sức:**`, `*   prograf`.
- **Filler N/A** dày đặc trong file dài (`Vị trí: N/A`, `Tần suất: N/A`) → không phải khái niệm y tế, dễ bị NER bắt nhầm.
- **Khoảng trắng thừa/không nhất quán** (nhiều space liên tiếp, tab, xuống dòng giữa cụm).
- ⚠️ **Hệ quả cho `position`**: đề chấm theo offset ký tự trên chuỗi input **gốc (chưa clean)**. Nếu normalize text để NER rồi không map ngược được offset về bản gốc → sai `position` → hỏng cả text_score. Cần một lớp giữ ánh xạ offset(clean → raw), hoặc chỉ tìm span trên raw text.

## 3. Quan sát theo từng loại khái niệm

| Type | Quan sát | Ghi chú xử lý |
|---|---|---|
| `TRIỆU_CHỨNG` | Nhiều nhất, mỗi file hàng chục cụm; cả VN lẫn EN (`ho`, `khó thở`, `ngất xỉu`, `nausea`); lặp lại nhiều lần trong cùng file (mục triệu chứng + mục diễn biến + mục đặc điểm) | Có thể xuất hiện >1 lần với position khác nhau; cần bắt hết các lần xuất hiện |
| `CHẨN_ĐOÁN` | Cụm bệnh VN: `tăng huyết áp`, `Đái tháo đường típ 2`, `bệnh thận mạn`, `hội chứng ruột kích thích`, `bệnh phổi tắc nghẽn mạn tính` | → map ICD-10 VN. 1 chẩn đoán có thể nhiều mã |
| `THUỐC` | Tên generic EN (`metoprolol`, `omeprazole`, `prednisone`, `amoxicillin`) + brand (`Lasix/Laxis`, `gleevec`, `prograf`, `coumadin`, `suboxone`, `z-pack`); thường kèm liều `25mg po bid` | → map RxNorm. Cần tách/không tách liều? (xem IDEAS). Có lỗi chính tả brand |
| `TÊN_XÉT_NGHIỆM` | `bạch cầu`, `creatinin`, `troponin`, `alt`, `ast`, `inr`, `WBC`, `x-quang ngực`, `điện tâm đồ (ecg)`, `tổng phân tích nước tiểu` | Không cần candidate/assertion |
| `KẾT_QUẢ_XÉT_NGHIỆM` | Giá trị + đơn vị: `39.2`, `3.0`, `0.10`, `176`, `240 đến 260`; đôi khi kèm đổi đơn vị `5.2 lên 6.3 mg/dl (460 - 557 umol/l)` | Cặp đôi với TÊN_XÉT_NGHIỆM; ranh giới value khó |

## 4. Phân bố assertion — proxy đo bằng feature-tagging (KHÔNG phải ground truth)

> Các số dưới đây là **proxy từ khớp regex** trên 100 file không nhãn (script `notebooks/eda_features.py`), không phải nhãn thật. Chúng chỉ ra "tín hiệu xuất hiện ở mức file", không phải số lượng assertion thật trên từng khái niệm. Phân bố thật chỉ có sau khi gán nhãn `data/labeled/`.

- **`isHistorical`** — tín hiệu phổ biến nhất: 93/100 file khớp cue tiền sử ("tiền sử", "trước khi nhập viện", "bệnh mạn tính"...). Rất mạnh theo **cấu trúc mục** (`1. Tiền sử bệnh`, "Thuốc trước khi nhập viện" gần như luôn historical) → rule section-aware có thể ăn điểm lớn.
- **`isNegated`** — proxy 82/100 file có cue phủ định (đã trừ false-friend). ⚠️ Bẫy đã xử lý trong tagging: `không xác định`/`không đặc hiệu`/`không rõ`/`không điển hình` là **một phần tên bệnh**, KHÔNG phải phủ định. Proxy này gần như chắc chắn *thổi phồng* số assertion thật (nhiều "không" mang nghĩa khác).
- **`isFamily`** — **rất hiếm khi tách đúng**: chỉ **2/100 file** có chủ thể người nhà mang bệnh (`84.txt`: nhiều thành viên gia đình cùng triệu chứng; `77.txt`: mẹ tử vong). Thêm **2 file** chỉ có "người nhà kể" (`23.txt`, `87.txt`) — đây là **narrator**, KHÔNG tạo isFamily (bẫy dễ gán nhầm). → class cực mất cân bằng; default conservative (không gán isFamily trừ khi rõ) hợp lý, nhưng phải bắt đúng vài ca hiếm.
- Lưu ý metric: assertions_score dùng Jaccard trung bình theo sample. Sample GT rỗng mà đoán rỗng → 1 điểm; đoán thừa → 0 điểm. → **thà bỏ sót hơn gán bừa** ở các loại hiếm.

## 5. Độ phủ knowledge base & chiến lược matching (đã test thực nghiệm)

Đã test độ phủ tên bệnh/thuốc xuất hiện trong 100 file so với `knowledge_base/*/processed/*.csv`. **Kết luận: KB đủ làm nền; vấn đề còn lại KHÔNG phải thiếu dữ liệu mà là lớp matching.**

### RxNorm (thuốc) — gần như 100% với tên chuẩn

- Test 38 tên thuốc thật (generic + brand) → **36/38 khớp** (`metoprolol`, `aspirin`, `gleevec`, `prograf`, `cellcept`, `coumadin`, `lasix`, `suboxone`, `klonopin`, `ranexa`, `azathioprine`, `tacrolimus`...).
- Thuốc trong text hầu hết viết tên tiếng Anh → dùng RxNorm EN trực tiếp, **không cần dịch**.
- 2 ca trượt: `laxis` (**typo** của lasix — bản đúng có trong KB) và `z-pack` (**tên lóng** của azithromycin). → gap là typo + tên lóng, không phải thiếu thuốc.

### ICD-10 (bệnh) — đủ, lợi thế 2 cột VN + EN bù nhau

- Exact-substring: cột `ten_benh_vi` **20/22** khớp, cột `disease_name_en` **12/13** khớp.
- ⚠️ **Hai cột bổ trợ nhau — nên match song song cả hai để tăng recall**: `rối loạn lưỡng cực` trượt cột VN (KB ghi "rối loạn cảm xúc lưỡng cực") nhưng `bipolar` khớp cột EN; ngược lại `gastroesophageal reflux` trượt cột EN (KB dùng "gastro-oesophageal") nhưng `trào ngược dạ dày` khớp cột VN.
- Ca trượt đều là paraphrase/đồng nghĩa/thứ tự từ (`tăng sản` vs `quá sản/phì đại tuyến tiền liệt`), không phải thiếu mã.

### Hệ quả cho `src/normalization`

- **Tên khái niệm có sẵn trong KB (recall khả thi)** — công việc chính là lớp matching, gồm: (1) **fuzzy match** cho typo/biến thể chính tả (RapidFuzz...); (2) **alias dict** nhỏ cho tên lóng/viết tắt (`z-pack`→azithromycin...); (3) **match song song cột VN + EN** của ICD-10; (4) xử lý **đồng nghĩa/thứ tự từ** (dense embedding giúp ở đây).
- ⚠️ Test này chỉ chứng minh tên **tồn tại** trong KB (recall). Việc **chọn đúng 1 mã** giữa nhiều ứng viên (vd nhiều mã ICD cùng khớp một chẩn đoán) là bài toán **ranking/disambiguation** riêng — nơi trọng số candidates 0.4 được quyết định.

## 6. Hệ quả từ metric (định hướng ưu tiên công sức)

`final = 0.3·text + 0.3·assertions + 0.4·candidates` (chi tiết: [TASK_SPEC.md](TASK_SPEC.md)).

- **candidates (0.4, khó nhất)**: chỉ tính trên `CHẨN_ĐOÁN`+`THUỐC`, lại **weighted theo số candidate ground-truth** → file nhiều mã bệnh/thuốc đóng góp nhiều điểm hơn. Đầu tư mapping ICD-10/RxNorm cho các file "đậm đặc" thuốc/chẩn đoán là đáng nhất.
- **text (0.3)**: WER trên trường text → boundary NER phải sát. Sai type = bị đếm 2 lần và 0 điểm cả 3 metric → **phân loại type đúng quan trọng ngang việc tìm đúng span**.
- **assertions (0.3)**: rule-based khai thác cấu trúc mục + cue phủ định có thể đạt phần lớn điểm với chi phí thấp → nên làm sớm như một "quick win".
- **Ưu tiên triển khai**: (1) eval harness + gán nhãn dev set → (2) NER + type → (3) assertion rule → (4) candidate mapping (đầu tư sâu nhất).

## 7. Checklist EDA — ĐÃ CHẠY (script `notebooks/eda_features.py`, output `notebooks/eda_outputs/`)

- [x] Thống kê phân bố độ dài, số dòng/file. → min=136, median=1229, max=4428 ký tự.
- [x] Section detector (đo `section_hits`): 99/100 file bán cấu trúc theo khung mục; chỉ 1 file freeform (`31.txt`).
- [x] Đếm dòng liều thuốc (`\d+\s?(mg|mcg|ml|g)` + route po/iv/bid...): 15 file "giàu thuốc".
- [x] Đo code-switching (tỉ lệ token thuần ASCII ≥4 ký tự): **61/100 file** có code-switching đáng kể → **cần bộ từ điển/xử lý EN↔VN** cho thuốc & triệu chứng.
- [x] Cue phủ định (đã lọc false-friend): 82/100 file.
- [x] Token dính liền (`camel-glue` lowercase→UPPER + cụm lặp): **27/100 file** — nhiễu đặc trưng, cần bước làm sạch an toàn offset.
- [x] Chọn 15 file đa dạng phủ đủ feature → `data/labeled/input/` + [`data/labeled/SELECTION.md`](../data/labeled/SELECTION.md).
- [x] Đối chiếu độ phủ tên bệnh/thuốc với KB (exact-substring) → RxNorm 36/38, ICD-10 VN 20/22 + EN 12/13. Chi tiết + chiến lược matching: **§5**.
- [ ] (còn lại) Đo tỉ lệ **disambiguation** (chọn đúng mã giữa nhiều ứng viên) — cần khi dựng `src/normalization` + KB index, và cần ground truth.
- [ ] (còn lại) Gán nhãn tay 15 file → `data/labeled/ground_truth/` (bước thủ công).

Kết quả chi tiết per-file: `notebooks/eda_outputs/feature_matrix.csv` (cờ + số đo từng file), `notebooks/eda_outputs/eda_report.md` (phân bố + bảng chọn mẫu + template train).
