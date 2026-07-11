# Dev/eval set — 15 file được chọn để gán nhãn tay

Chọn từ 100 file `data/raw/input/` bằng greedy set-cover trên các feature EDA (script: [`../../notebooks/eda_features.py`](../../notebooks/eda_features.py), báo cáo đầy đủ: [`../../notebooks/eda_outputs/eda_report.md`](../../notebooks/eda_outputs/eda_report.md)). Mục tiêu: 15 file này phủ **toàn bộ** đặc điểm/nhiễu tìm được trong EDA, để khi tự chấm điểm ta đánh giá được khả năng xử lý từng loại vấn đề.

File input đã copy sẵn vào `input/`. Cần gán nhãn tay → lưu `ground_truth/{i}.json` tương ứng (format: xem [`../../docs/TASK_SPEC.md`](../../docs/TASK_SPEC.md)).

## 15 file & feature phủ

| file | đặc điểm nổi bật cần test |
|---|---|
| 3.txt | dài nhất nhóm, giàu N/A filler, markdown `**`, nhiều xét nghiệm + kết quả, glue |
| 31.txt | **ngắn + freeform** (sản khoa, không theo khung mục), viết tắt `FM+/VB-/LOF-`, glue |
| 84.txt | **isFamily thật** ("nhiều thành viên trong gia đình có triệu chứng tương tự") |
| 87.txt | **narrator** ("người nhà kể") — bẫy: KHÔNG được gán isFamily |
| 36.txt | giàu thuốc + xét nghiệm, có markdown |
| 82.txt | giàu thuốc + xét nghiệm + glue |
| 51.txt | giàu thuốc + xét nghiệm + glue |
| 37.txt | giàu thuốc + xét nghiệm + glue |
| 70.txt | giàu thuốc + xét nghiệm, tiền sử |
| 91.txt | xét nghiệm + glue |
| 97.txt | giàu thuốc + xét nghiệm |
| 66.txt | xét nghiệm + glue + tiền sử |
| 35.txt | xét nghiệm + glue, thuốc brand (gleevec), nhiều chẩn đoán mạn tính |
| 50.txt | giàu thuốc (hen suyễn), glue (`tạiBệnh`), code-switching mạnh |
| 54.txt | **dài**, xét nghiệm + glue + tiền sử |

Coverage: mọi feature đều ≥1 file (chi tiết bảng trong `eda_report.md`). Các feature toàn cục hiếm (`f_freeform`=1, `f_markdown`=2, `f_na`=1, `f_family`=2) gần như dồn hết vào dev set — xem phần train bên dưới.

## Đảm bảo TRAIN cũng có các feature này (yêu cầu: cả train & test cùng có)

`data/raw/input/` là test của BTC — **không được dùng train**. Nên feature trong train phải đến từ `data/synthetic/` (tự sinh). Hai nhóm:

1. **Feature còn nhiều file BTC ngoài dev** → dùng làm *template văn phong* khi sinh synthetic (không train trực tiếp trên chúng):
   - `f_glue` (token dính liền): còn 15 file, vd `4, 24, 32, 47, 56, 58, 74, 75, 83, 85, 88, 92, 94, 98, 100`.
   - `f_codeswitch`: 61 file. `f_drug`: 8 file. `f_lab`: 6 file. `f_short`: 12 file. `f_neg`, `f_history`: rất nhiều.
   - `f_family`: còn `77.txt` (mẹ tử vong). `f_narrator`: còn `23.txt`.
2. **Feature toàn cục hiếm, không còn template BTC** (`f_freeform`, `f_markdown`, `f_na`) → khi sinh synthetic phải **chủ động chèn bằng code** (rải `**bold**`, `N/A`, viết freeform không theo khung mục), không phụ thuộc template.

→ Khi viết script sinh synthetic (`scripts/` + `data/synthetic/`), checklist bắt buộc: mỗi feature ở bảng trên phải xuất hiện trong train với tần suất hợp lý, đặc biệt **token dính liền** và **code-switching** (nhiễu đặc trưng của bộ này).
