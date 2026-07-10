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

## 4. Phân bố assertion (định hướng, chưa có ground truth)

- **`isHistorical`** — phổ biến nhất. 90/100 file có chữ "tiền sử". Tín hiệu mạnh theo **cấu trúc mục**: mọi thứ trong `1. Tiền sử bệnh` và `Thuốc trước khi nhập viện` gần như luôn historical. → một luật section-aware có thể ăn điểm lớn.
- **`isNegated`** — phổ biến. 84/100 file có "không". Cue rõ: `Không buồn nôn`, `chưa ra huyết (VB -)`, `âm tính`, `loại trừ`, `không ghi nhận`. ⚠️ Bẫy: `không xác định`/`không đặc hiệu`/`không rõ` là **một phần tên bệnh**, KHÔNG phải phủ định → cần loại trừ khỏi rule negation.
- **`isFamily`** — **hiếm**. Chỉ ~9/100 file nhắc tới người nhà, và phần lớn "người nhà" chỉ đóng vai **người kể chuyện** ("theo lời người nhà kể"), KHÔNG phải chủ thể mang bệnh. Trường hợp thật (người nhà mắc bệnh) gần như không thấy trong mẫu quan sát. → class cực mất cân bằng; default "không gán isFamily" có thể đã tốt, nhưng cần bắt đúng vài ca hiếm để không mất điểm Jaccard.
- Lưu ý metric: assertions_score dùng Jaccard trung bình theo sample. Sample không có assertion nào (GT rỗng) mà mình đoán rỗng → được 1 điểm; đoán thừa → 0 điểm. → **thà bỏ sót (conservative) hơn gán bừa** ở các loại hiếm.

## 5. Hệ quả từ metric (định hướng ưu tiên công sức)

`final = 0.3·text + 0.3·assertions + 0.4·candidates` (chi tiết: [TASK_SPEC.md](TASK_SPEC.md)).

- **candidates (0.4, khó nhất)**: chỉ tính trên `CHẨN_ĐOÁN`+`THUỐC`, lại **weighted theo số candidate ground-truth** → file nhiều mã bệnh/thuốc đóng góp nhiều điểm hơn. Đầu tư mapping ICD-10/RxNorm cho các file "đậm đặc" thuốc/chẩn đoán là đáng nhất.
- **text (0.3)**: WER trên trường text → boundary NER phải sát. Sai type = bị đếm 2 lần và 0 điểm cả 3 metric → **phân loại type đúng quan trọng ngang việc tìm đúng span**.
- **assertions (0.3)**: rule-based khai thác cấu trúc mục + cue phủ định có thể đạt phần lớn điểm với chi phí thấp → nên làm sớm như một "quick win".
- **Ưu tiên triển khai**: (1) eval harness + gán nhãn dev set → (2) NER + type → (3) assertion rule → (4) candidate mapping (đầu tư sâu nhất).

## 6. Checklist EDA cần chạy bằng code (chưa làm — để trong notebooks/)

- [ ] Thống kê phân bố độ dài, số dòng, số bullet/ file (histogram).
- [ ] Đếm tần suất header mục để chuẩn hoá bộ "section detector" (các biến thể: "Bệnh sử hiện tại" vs "Lịch sử bệnh hiện tại" vs "Tiền sử bệnh hiện tại").
- [ ] Trích toàn bộ dòng khớp regex liều thuốc (`\d+\s?(mg|mcg|ml|g)`) → ước lượng số THUỐC/file, độ phủ tên thuốc so với RxNorm.
- [ ] Trích ứng viên CHẨN_ĐOÁN (dòng trong mục bệnh mạn tính/lý do nhập viện) → đối chiếu tỉ lệ match ICD-10 VN (exact/fuzzy).
- [ ] Đo mức độ code-switching (tỉ lệ token EN) để quyết định có cần bộ từ điển/dịch thuốc–triệu chứng EN↔VN.
- [ ] Thống kê cue phủ định & vị trí, lọc các false-friend ("không xác định"...).
- [ ] Đo trùng lặp token dính liền (regex phát hiện `(\w{4,})\1`) → thiết kế bước làm sạch an toàn cho offset.
- [ ] Chọn ~15–20 file đa dạng (ngắn/dài, giàu thuốc/giàu triệu chứng/có phủ định/có người nhà) để gán nhãn tay làm `data/labeled/` dev set.
