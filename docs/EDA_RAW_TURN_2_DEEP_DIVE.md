# EDA sâu `raw_turn_2` — cấu trúc, montage và hàm ý cho pipeline

Ngày phân tích: **2026-07-24**  
Phạm vi: toàn bộ 100 file trong `data/raw_turn_2/input/`  
Trạng thái nhãn: **không có ground truth**

Artifacts tái lập cho **phần thống kê tự động**:

- Script: [`../notebooks/20260724_eda_raw_turn_2_structure.py`](../notebooks/20260724_eda_raw_turn_2_structure.py)
- Feature matrix 100 file: [`../notebooks/eda_outputs/turn2_structure_features.csv`](../notebooks/eda_outputs/turn2_structure_features.csv)
- Các cặp tái sử dụng nội dung: [`../notebooks/eda_outputs/turn2_reuse_pairs.csv`](../notebooks/eda_outputs/turn2_reuse_pairs.csv)
- Các dòng lặp giữa file: [`../notebooks/eda_outputs/turn2_repeated_lines.csv`](../notebooks/eda_outputs/turn2_repeated_lines.csv)
- Tổng hợp máy đọc được: [`../notebooks/eda_outputs/turn2_structure_summary.json`](../notebooks/eda_outputs/turn2_structure_summary.json)

Chạy lại bằng:

```bash
python notebooks/20260724_eda_raw_turn_2_structure.py
```

Đây là EDA, không phải một lần chạy model/pipeline, nên không tạo `exp_*` và không ghi
`EXPERIMENTS_LOG.md`.

Các bảng phân loại thủ công trong báo cáo là snapshot có thể audit lại từ raw file, nhưng không
được script tự động sinh và không phải nhãn dùng cho model.

---

## 1. Kết luận quan trọng nhất

Insight “phân loại sample theo cấu trúc” là đúng, nhưng **đơn vị xử lý không nên là cả
sample/file**. `raw_turn_2` có bằng chứng rất mạnh của việc **lắp ghép nhiều đoạn nguồn**:
một file thường đổi qua lại giữa bệnh án, câu hỏi người dùng, câu trả lời bác sĩ và bài giáo
dục sức khỏe. Không hiếm cấu trúc `A → B → A`, và ranh giới đôi khi nằm ngay giữa một dòng.

Nói ngắn gọn:

1. Cần tách **thể loại ngữ nghĩa**, **layout bề mặt** và **nhiễu/montage** thành ba trục
   độc lập. Một nhãn duy nhất như “file Q&A” hoặc “file bệnh án” sẽ làm mất thông tin.
2. Router nên hoạt động ở **segment/span-window level**, multi-label, rồi mới áp policy NER,
   assertion và linking phù hợp cho từng segment.
3. Router trước mắt chỉ nên **đổi context/policy**, không tự động xóa đoạn “lạc chủ đề”.
   Không có ground truth nên chưa biết BTC có annotate khái niệm trong donor block hay không.
4. Mọi segmentation/normalization phải bảo toàn ánh xạ về chuỗi raw. Với phát hiện mới rằng
   BTC chấm `position` rất chặt, việc reflow hoặc NFC-normalize trực tiếp input là rủi ro lớn.
5. Mức tái sử dụng nội dung giữa file rất cao, nên số **tài liệu độc lập hiệu dụng** nhỏ hơn
   100; báo cáo không ước lượng một con số effective sample size cụ thể. Nếu gán nhãn subset
   chỉ để evaluation (không train), phải group-split theo reuse family, không random từng file.

### Bốn con số tóm tắt

| Quan sát | Kết quả |
|---|---:|
| Có ít nhất một heading bệnh án chuẩn `1./2./3.` | **72/100** |
| Có đủ đúng chuỗi heading `1 → 2 → 3` | **21/100** |
| Có ít nhất một marker hỏi hoặc trả lời | **59/100** |
| Đồng thời có marker Q&A và heading bệnh án | **35/100** |

Điều này giải thích vì sao một rule “nếu có `Câu hỏi từ người dùng` thì coi cả file là Q&A”
hoặc “nếu có `1. Tiền sử bệnh` thì coi cả file là bệnh án” sẽ sai trên nhiều file.

---

## 2. Phương pháp và giới hạn diễn giải

EDA dùng hai lớp:

1. **Tự động, tái lập được**:
   - thống kê độ dài/dòng/paragraph và regex word unit;
   - marker heading, Q&A, bullet;
   - redaction, placeholder, Unicode, glue và repetition;
   - exact normalized token 7/8/12-gram giữa mọi cặp file;
   - exact normalized line dài ít nhất 45 ký tự.
2. **Đọc thủ công đủ 100 file**:
   - xác định register mở đầu;
   - nhận diện đổi chủ đề, đoạn chèn và topology montage;
   - kiểm tra Q&A cùng chủ đề/sai chủ đề/thiếu một phía;
   - audit các ca biên mà regex không thể hiểu ngữ nghĩa.

Các nhãn trong EDA là **feature mô tả**, không phải ground truth NER và không được dùng làm
output. Nhận định “donor”, “montage”, “lạc chủ đề” chỉ nói về sự không liên tục của nội dung;
nó **không chứng minh** đoạn đó bị loại khỏi nhãn kín của BTC.

Theo quy tắc chống leakage của repo, `raw_turn_2`:

- không được dùng làm dữ liệu train;
- không được dùng làm template sinh synthetic;
- không được hard-code file ID/câu chữ vào router;
- chỉ được dùng để rút ra thiết kế tổng quát và để đánh giá/ablation đúng luật.

---

## 3. Kích thước và mức độ bị “flatten”

| Chỉ số | Min | P25 | Median | P75 | Max |
|---|---:|---:|---:|---:|---:|
| Ký tự/file | 1.293 | 1.583 | 1.838 | 2.370 | 4.481 |
| Regex word unit/file | 264 | 325 | 383 | 489 | 954 |
| Dòng vật lý/file | 2 | 18 | 29 | 36 | 93 |
| Dòng không rỗng/file | 2 | 17 | 26 | 35 | 77 |
| Độ dài dòng lớn nhất/file | 111 | 241 | 416 | 590 | 1.890 |

Toàn corpus có **203.817 ký tự**, **42.438 regex word unit** và **3.028 dòng vật lý**.
`TOKEN_RE=\w+` sau NFC chỉ dùng để đo reuse; đây không phải BPE token của model hay tách từ
tiếng Việt về mặt ngôn ngữ.

Nhiều file dài nhưng ít newline:

| Tín hiệu | Số file |
|---|---:|
| Có dòng dài ít nhất 300 ký tự | **65** |
| Có dòng dài ít nhất 500 ký tự | **34** |
| Có dòng dài ít nhất 1.000 ký tự | **12** |
| `≤5` dòng không rỗng và trung bình `>300` ký tự/dòng | **4** |

Mười hai file có dòng `≥1.000` ký tự:
`7, 9, 30, 35, 44, 56, 67, 71, 76, 83, 86, 94`.

Ba ca gần như collapse toàn bộ newline là `76` (3 dòng), `83` (2 dòng), `94` (3 dòng).
`48` có 5 dòng không rỗng nhưng vẫn rất dày. Vì vậy:

- line-based parser chỉ là một nguồn boundary candidate;
- heading/Q&A marker phải được tìm **ở mọi vị trí trong dòng**;
- cần sentence boundary và semantic change-point dự phòng.

---

## 4. Taxonomy đúng: hai trục chính, không phải một nhãn file

### 4.1. Trục A — opening wrapper/anchor proxy

Đây là nhãn **exclusive theo wrapper/cue cấu trúc xuất hiện đầu tiên**, không phải semantic
genre vàng và không đại diện toàn file. Khi wrapper và nội dung mâu thuẫn, tie-break ưu tiên
wrapper bề mặt.

| Register mở đầu | Số file | File |
|---|---:|---|
| Q&A người dùng–bác sĩ | 42 | 7, 9, 13, 14, 16, 17, 19, 20, 21, 25, 27, 28, 32, 34, 35, 37, 41, 48, 49, 52, 54, 55, 56, 59, 60, 61, 64, 65, 66, 67, 71, 75, 78, 79, 80, 81, 84, 86, 93, 95, 96, 100 |
| Bệnh án/case bệnh nhân | 47 | 3, 4, 5, 6, 8, 10, 11, 12, 15, 22, 23, 24, 29, 30, 31, 33, 36, 38, 39, 40, 42, 43, 45, 46, 47, 50, 51, 53, 57, 58, 63, 68, 69, 70, 73, 74, 77, 82, 85, 87, 88, 89, 91, 92, 97, 98, 99 |
| Bài/định nghĩa sức khỏe | 4 | 1, 2, 18, 26 |
| Fragment/continuation mồ côi | 7 | 44, 62, 72, 76, 83, 90, 94 |

Ví dụ `1.txt` là article-led dù có một heading bệnh án bị chèn; `3.txt` được xếp clinical-led
vì wrapper là `1. Tiền sử`, dù nội dung mạch lạc đầu lại là đuôi Q&A về thuốc. Đây chính là lý
do proxy này chỉ dùng điều hướng audit và phải thêm trục B.

### 4.2. Trục B — cấu trúc xuất hiện ở bất kỳ vị trí nào

Các state cấu trúc nên là multi-label:

- `QUESTION`;
- `DOCTOR_ANSWER / EDUCATIONAL_ANSWER`;
- `HEALTH_ARTICLE`;
- `CLIN_HISTORY`;
- `CLIN_CURRENT`;
- `CLIN_EVAL / LAB / IMAGING`;
- `MEDICATION_OR_PROCEDURE_LIST`;
- `ORPHAN / UNKNOWN`.

Một file có thể mang nhiều state, lặp state, hoặc quay lại state cũ sau donor block.

### 4.3. Heading bệnh án chuẩn: đa số chỉ giữ một phần khung

Detector được thiết kế để không đếm các article heading thông thường:

- H1: `1.` + `Tiền sử/Lịch sử`;
- H2: `2.` + `Tiền sử/Bệnh sử/Lịch sử`;
- H3: `3.` + `Đánh giá/Khám/Thăm khám`.

Regex tìm ở mọi vị trí trong raw line và chấp nhận 0–3 space sau số.

| Chuỗi heading quan sát | Số file | Ý nghĩa |
|---|---:|---|
| Không có | 28 | Không mang numbered clinical frame |
| `1 → 2 → 3` | **21** | Có đúng marker sequence, đúng thứ tự, không lặp |
| `1 → 2` | 17 | Thiếu phần 3 |
| Chỉ `2` | 13 | Fragment bắt đầu giữa case |
| Chỉ `3` | 10 | Fragment đánh giá hoặc heading chèn |
| `2 → 3` | 6 | Thiếu phần 1 |
| Chỉ `1` | 2 | Chỉ còn tiền sử |
| `1 → 3` | 2 | Thiếu phần 2 |
| `1 → 2 → 2` | 1 | Heading 2 lặp/glue, chính là `82.txt` |

Như vậy **72 file có dấu vết khung bệnh án nhưng 51/72 có marker sequence thiếu/lặp/malformed**.
Con số cũ “khoảng 70 file vẫn giữ frame” đúng về hướng, nhưng che mất việc chỉ 21 file có đúng
chuỗi marker `1 → 2 → 3`. Ngay cả 21 file này vẫn có thể chứa montage; regex không chứng minh
toàn frame mạch lạc về ngữ nghĩa.

### 4.4. Bullet/list là phổ biến nhưng không ổn định

| Tín hiệu | Kết quả |
|---|---:|
| Có dash bullet | 88 file, 1.141 dòng |
| Có bullet `•` | 12 file, 136 dòng |
| Trộn cả dash và `•` | 10 file |
| Có numbered line start | 77 file |
| Không có list marker nào | 3 file: `71, 76, 94` |

Phân bố tổng marker dòng:

| Marker/file | Số file |
|---:|---:|
| 0 | 3 |
| 1–4 | 24 |
| 5–9 | 17 |
| 10–19 | 24 |
| ≥20 | 32 |

Nghĩa là bullet density hữu ích cho router nhưng không thể là điều kiện bắt buộc. Ngoài ra,
bullet có thể bị glue sau prose trên cùng dòng, ví dụ `4, 5, 43, 51, 88, 91`.

---

## 5. Q&A: marker không đồng nghĩa với một cặp hợp lệ

### 5.1. Ma trận marker

Detector chấp nhận các biến thể như `Hỏi :`, `Trả lời :`, `Bác sĩ trả lời`,
`Câu hỏi từ người dùng`, `Câu hỏi của người dùng gửi đến hệ thống`, có hoặc không có dấu `:`.

| Cấu trúc marker | Số file |
|---|---:|
| Có cả question và answer | **35** |
| Chỉ question | 11 |
| Chỉ answer | 13 |
| Không có marker | 41 |
| Có ít nhất một phía | **59** |

Có **35 file** đồng thời chứa Q&A marker và ít nhất một numbered clinical heading. Vì vậy
marker thường chỉ là wrapper hoặc một boundary cục bộ, không phải nhãn cho cả document.

### 5.2. Audit ngữ nghĩa 59 file có marker

Đọc thủ công quan hệ Q↔A cho kết quả:

| Trạng thái | Số file | Tỷ lệ |
|---|---:|---:|
| Cùng chủ đề, kể cả có donor block chen giữa | 37 | 62,7% |
| Sai chủ đề rõ ràng | 9 | 15,3% |
| Thiếu một phía/không đủ chắc chắn | 13 | 22,0% |

Chín ca mismatch rõ:

- `35`: question là stress test/đau ngực, answer là viêm hang vị;
- `56`: question là kết quả bệnh ba thân động mạch vành, answer là viêm hang vị;
- `67`: question là list suy tim/PVD/COPD/ung thư dương vật, answer là viêm hang vị;
- `71`: question là note tự tử/cắt cụt hai chân, answer hỏi về mẩn ngứa lưng;
- `75`: question staging u trực tràng, answer nấm bẹn;
- `84`: question chỉ có “thuốc giảm đau opioid”, answer nấm bẹn;
- `86`: question ho/nghẹt ngực/khó thở, answer viêm hang vị;
- `96`: hẹp 80% động mạch thận, sau đó là tư vấn chăm sóc môi phun xăm;
- `98`: question tàn nhang/nghệ mật ong, sau marker answer lại là bệnh sử tâm thần/tự tử.

Trong riêng 35 file đủ cả marker Q và A: **28 matched, 7 mismatch**.

Một ngưỡng lexical overlap đơn giản không đủ. Ví dụ trong feature matrix:

- `25.txt` là Q&A cùng chủ đề nhưng content-token Jaccard chỉ khoảng `0,019`;
- `35.txt` là mismatch rõ nhưng Jaccard khoảng `0,112`.

Pairer cần ba trạng thái `matched / mismatched / unpaired`, dùng medical anchors, body system,
ontology, actor và semantic similarity; không nên ép nearest Q với nearest A.

### 5.3. Q&A implicit và one-sided không có marker

Ma trận 59 file ở trên là statistic chính vì có detector tái lập. Audit thủ công mở rộng, chủ
quan hơn, còn thấy:

- `1, 2, 26` là FAQ/article cùng chủ đề dù không có strict Q&A marker;
- 23 file mang question-only hoặc answer-only fragment không marker:
  `4, 5, 11, 15, 23, 33, 39, 42, 43, 50, 62, 68, 70, 72, 73, 74, 82, 85, 88, 89, 91, 92, 94`;
- chỉ 15 file không có đủ cue để gọi là Q&A carrier:
  `6, 8, 10, 18, 24, 36, 40, 45, 46, 53, 57, 58, 77, 87, 99`.

Theo phạm vi manual mở rộng này, **85/100** file mang ít nhất một Q&A/FAQ relation hoặc
one-sided fragment: 40 matched, 9 mismatch rõ, 36 incomplete/uncertain. Con số này không thay
thế ma trận strict 59 file; nó chỉ cho thấy pairer không thể phụ thuộc hoàn toàn vào marker.

---

## 6. Montage và tái sử dụng chunk là quy luật chính

### 6.1. Triage thủ công về seam

Đây là **single-review manual triage**, không phải nhãn tái lập bằng regex. Reviewer cân nhắc
đồng thời độ dài donor block, mức đổi chủ đề/giọng kể, khả năng `A → B → A`, numbering reset và
độ chắc chắn. Hai mức dưới đây là snapshot phục vụ audit, không phải một rubric cứng theo số
dòng và tuyệt đối không được đưa file ID vào router:

- **macro/obvious montage**: đổi nguồn/chủ đề tương đối rõ;
- **localized/borderline seam**: intrusion ngắn, format collision hoặc bằng chứng ngữ nghĩa
  chưa đủ mạnh.

Kết quả:

| Mức | Số file |
|---|---:|
| Macro/obvious montage | **71** |
| Localized/borderline seam | 29 |

Trong lần review này, reviewer tìm thấy ít nhất một seam hoặc format intrusion đáng nghi ở mọi
file. Đây là manual hypothesis, không phải fact vàng. Nó **không có nghĩa** 71 file chứa “text
vô dụng” hoặc donor block chắc chắn không có gold.

Danh sách macro/obvious montage:

`2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 42, 43, 44, 45, 46, 49, 50, 51, 53, 54, 55, 56, 58, 59, 60, 61, 62, 63, 67, 68, 69, 71, 72, 75, 76, 77, 78, 80, 83, 86, 87, 88, 91, 94, 95, 96, 97, 98, 99`.

Danh sách localized/borderline seam:

`1, 10, 13, 15, 24, 27, 28, 40, 41, 47, 48, 52, 57, 64, 65, 66, 70, 73, 74, 79, 81, 82, 84, 85, 89, 90, 92, 93, 100`.

Con số `37/100` trong EDA trước đây là một lower bound hẹp cho các block article/Q&A rất lộ.
Triage mới mở rộng sang reverse injection, clinical→clinical merge, one-sided fragments và
interleaving nên flag nhiều file hơn; con số 71 cần được hiểu là manual severity judgment.

### 6.2. Các topology điển hình

| Topology | Ví dụ | Quan sát |
|---|---|---|
| `A + B` | `3` | Đuôi Q&A thuốc → bệnh án stroke |
| `A + B` | `44` | Fragment lâm sàng → answer mày đay |
| `A + B + A` | `26` | Bài CAD → case túi mật → quay lại dự phòng CAD |
| `A + B + A` | `42` | Bệnh án → câu hỏi viêm hang vị → quay lại bệnh án |
| `A + B + A` | `60` | Tư vấn acne → case chống đông → quay lại kết luận acne |
| `A + B + A` | `78` | Q&A chảy máu cam → wound case → quay lại answer |
| Heading reset | `8` | Clinical `1/2/3` → bài Kawasaki tiếp tục từ mục 6 |
| Same-line glue | `62` | Kết thúc advice rồi dính ngay `2. Tiền sử...` |
| Same-line glue | `48` | `3. Đánh giá tại bệnh việnDù...` |
| Repeated heading | `82` | `2.` standalone rồi lặp `2...hiện tạiBệnh nhân...` |

Router cần cho phép quay lại state A sau B; một segmentation tuyến tính “Q rồi phần còn lại là A”
không đủ.

### 6.3. Bằng chứng định lượng cross-file

Chuẩn hóa dùng NFC + lowercase + word tokenization, sau đó chỉ so exact shingle. Đây là phép đo
bảo thủ: paraphrase hoặc bản dịch lỗi sẽ không được tính là trùng.

Không có cặp file nào byte-identical toàn văn. Sự lặp nằm ở **chunk**, không phải duplicate
nguyên document.

| Chỉ số | Kết quả |
|---|---:|
| File có ít nhất một exact repeated line `≥45` ký tự | **83** |
| File có ít nhất 2 repeated line như trên | **69** |
| File có ít nhất 5 repeated line như trên | **48** |
| Median tỷ lệ 7-gram của một file xuất hiện ở file khác | **67,4%** |
| Mean tỷ lệ trên | **55,3%** |
| File có reused 7-gram ratio `≥50%` | **58** |
| File có ratio `≥75%` | **44** |
| File có ratio `≥90%` | **27** |
| Exact 8-gram nearest-neighbor containment `≥30%` | **67 file** |
| Exact 8-gram nearest-neighbor containment `≥50%` | **53 file** |
| Exact 8-gram nearest-neighbor containment `≥75%` | **38 file** |

Graph nối hai file khi exact 8-gram containment trên file ngắn hơn `≥45%` tạo **22 component,
phủ 56 file**. Một số family:

- rabies: `13, 16, 20`;
- mày đay: `14, 19, 28, 52`;
- amyloidosis: `21, 32, 79`;
- acne: `41, 59, 60`;
- dị tật tai: `37, 48`;
- alopecia: `49, 65`;
- gout/tophi: `80, 95`;
- hydrocephalus/papilledema: `23, 45, 50`.

Hai ví dụ bridge-document đặc biệt:

- component `35, 56, 67, 86, 89, 94` nối source stress-test với source bài viêm hang vị vì
  `35` mang cả hai;
- component `30, 44, 76, 83` chia sẻ một answer mày đay bị dịch máy hỏng nhưng có prefix
  lâm sàng khác nhau.

Ngoài ra `2/8` chứa các fragment bổ trợ nhau của bài Kawasaki, còn `26/18` có các fragment bổ
trợ nhau của bài CAD — **consistent with** giả thuyết source split/recombination, chưa phải
provenance đã biết. Tổng hợp các bằng chứng, giả thuyết hợp lý nhất là dữ liệu được recombine
từ một **chunk bank**, thay vì 100 tài liệu độc lập.

---

## 7. Các lớp nhiễu cơ học

### 7.1. Redaction và placeholder

| Nhiễu | Kết quả |
|---|---:|
| Redaction `***` | **99 run trong 30 file**, dài 3–36 dấu `*` |
| Bracket placeholder | **24 lần trong 5 file** |

Placeholder:

- `[Ngày]`: 9;
- `[Date]`: 7;
- `[Số]`: 3;
- `[Tên cuộc họp]`: 2;
- `[Name]`: 2;
- `[Tên bác sĩ]`: 1.

Redaction gần như luôn nằm ở tên thuốc/sản phẩm/điều trị. Không có lexical identity thì:

- không thể suy RxNorm đáng tin;
- không nên hallucinate candidate;
- nếu BTC vẫn annotate span `*******` là `THUỐC`, policy hợp lý nhất có thể là nhận diện loại
  nhưng abstain candidate — cần leaderboard/gold evidence trước.

### 7.2. Unicode và whitespace

- **20 file không ở NFC**, tổng 1.018 combining mark:
  `13, 14, 16, 17, 19, 20, 28, 34, 35, 42, 52, 54, 56, 67, 72, 81, 86, 94, 97, 100`.
- Zero-width space xuất hiện 14 lần trong `22, 69`.
- NBSP xuất hiện 4 lần trong `80, 95`.
- 66 file có trailing space, tổng 278 dòng.
- Một file dùng tab; không có CR/BOM.

Không có Markdown heading/bold thật. Regex cũ thấy `**` chủ yếu vì redaction star-run; không nên
gọi đó là Markdown noise.

**Hệ quả offset:** NFC có thể thay đổi số code point. Chỉ normalize trên shadow text có
`clean_index → raw_index`; tuyệt đối không thay chuỗi đầu vào dùng để xuất `position`.

### 7.3. Glue, repetition và dịch máy lỗi

Legacy proxy `camel lower→UPPER OR repeated phrase` (được tái lập trong script mới để đối chiếu
lịch sử) flag **55/100 file**. Đây là cờ screening rộng, không phải mọi hit đều là lỗi. Các mẫu
rõ:

- `thuốcVastarel`;
- `doxycyclinebactrim`;
- `klonopinclonidine`;
- `bệnhgout`, `urictăng`;
- `hiện tạiBệnh nhân`;
- `182bạch cầuvài`;
- `vancozosynbactrim`;
- `việnDù`.

Có **33** dấu kết câu dính chữ hoa ở **15** file. Với ngưỡng dòng chuẩn hóa dài ít nhất 30 ký
tự, có **17** exact repeated-line type nội bộ, tạo 17 bản sao thừa trong 11 file. Regex
adjacent-word cũng bắt cả lặp hợp lệ như `từ từ`, `dần dần`, nên không được clean mù quáng.

Nhóm `30/44/76/83` lặp cùng bản dịch máy hỏng của answer mày đay, ví dụ:

- `tế bào mast` biến thành `tế bào cột sống`;
- một câu về nhuộm miễn dịch biến thành
  `Quảng cáo quảng cáo thiết bị thương mại miễn phí...`;
- `điều trị triệu chứng` biến thành `Quá giá trị chỉ là giấy chứng nhận`.

`22/69` chia sẻ một question mày đay bị hỏng nặng và có zero-width space. Điều này cho thấy
noise không chỉ là typo độc lập; một chunk lỗi có thể được tái sử dụng nhiều lần.

### 7.4. Lab, đơn vị, thuốc và code-switch

- Có 65 trường hợp số–đơn vị dính nhau trong 32 file. Đây là tokenization hazard proxy, không
  mặc định là malformed vì `325mg` hoặc `4mm` có thể là cách viết hợp lệ.
- Có nhiều biến thể case/decimal/spacing: `37^∘ 8`, `HbA1c 7,5 pP%`, `3L4`,
  `hct 8.126.3`, `182bạch cầuvài`.
- Full English phrase rõ ở một số file (`intravenous fluids`, `nausea/diarrhea/abdominal
  pain`, `iv lasix...once`); acronym/tên thuốc English phổ biến hơn nhiều.

Proxy “ASCII word ≥4 ký tự” flag 100/100 nhưng overcount từ tiếng Việt không dấu. Vì vậy số
`99/100 code-switch` cũ không nên được hiểu là 99 file đều có English phrase; cần tách:

1. full English phrase;
2. acronym/test/drug token;
3. tiếng Việt không dấu.

---

## 8. Audit ba file người dùng nêu

### `1.txt` — article-led nhưng không sạch

- 4.481 ký tự, 59 dòng raw/40 dòng không rỗng.
- Bài định nghĩa/giáo dục sức khỏe về thiếu men G6PD.
- Có article heading `1/2/3/4`, 19 bullet `•`.
- Một canonical clinical H3 bị chèn vào dòng symptom:
  `3. Đánh giá tại bệnh viện • Tim đập nhanh, khó thở`.
- Ba dòng thuốc bị redaction star-run.

Kết luận: đúng là “dạng định nghĩa bệnh”, nhưng phải gắn thêm cờ
`article + clinical-heading intrusion + inline bullet + redaction`.

### `81.txt` — Q&A đúng chủ đề, có clinical tail

- 1.516 ký tự, 10 dòng raw/7 dòng không rỗng.
- Có đủ marker question/answer.
- Question và answer cùng chủ đề thrombophilia, sảy thai, chống đông trong thai kỳ.
- Kết thúc bằng donor line không liên quan:
  `Các thủ thuật đã thực hiện: đặt shunt dẫn lưu tĩnh mạch cửa qua da`.
- Không có canonical numbered clinical heading.

Kết luận: Q&A marker đúng nhưng file vẫn không thuần Q&A. Router cần tách tail, song chưa được
tự động bỏ entity trong tail nếu chưa biết gold policy.

### `82.txt` — duplicate/glued heading và sandwich nhỏ

- 1.502 ký tự, 19 dòng raw/18 dòng không rỗng.
- Canonical sequence `1 → 2 → 2`; không có H3.
- H2 đầu là standalone, H2 sau lặp và glue:
  `2. Tiền sử bệnh hiện tạiBệnh nhân nhập viện...`.
- Sau prose mới quay lại bullet.
- Hai dòng advice amyloidosis chen vào case sỏi ống mật rồi case tiếp tục.

Kết luận: đây là ví dụ tốt nhất cho:

- repeated heading;
- heading–body glue;
- prose trước bullet;
- `A → B → A`;
- lý do parser phải tìm seam ở character level chứ không chỉ line level.

---

## 9. Hàm ý cho hướng giải mới

### 9.1. Giả thuyết cần tách rõ

Không có nhãn nên hiện có ít nhất ba khả năng:

1. **Annotate mọi medical mention** trong mọi block. Khi đó donor block không phải distractor
   về mặt output; router chỉ giúp context và type/assertion.
2. **Chỉ annotate focal/patient block**. Khi đó article/Q&A donor là distractor, suppression
   có thể tăng precision rất mạnh.
3. **Annotate theo role**: patient mention được tag, generic explanation không tag hoặc tag khác
   nhau theo type. Đây là khả năng phù hợp với mô tả `TRIỆU_CHỨNG = triệu chứng bệnh nhân mắc`,
   nhưng vẫn chưa được chứng minh.

Không được chốt khả năng 2 chỉ dựa vào cảm giác “lạc đề”. Cần ablation code tự động và điểm BTC.

### 9.2. Cấu trúc router đề xuất

```text
raw document
    ↓  (chỉ đọc; giữ nguyên ký tự)
candidate seams ở character offsets
    ↓
segment/window multi-label
    ├─ QUESTION
    ├─ DOCTOR_ANSWER / ARTICLE
    ├─ CLIN_HISTORY
    ├─ CLIN_CURRENT
    ├─ CLIN_EVAL / LAB / IMAGING
    └─ OTHER
    ↓
policy NER + assertion + linking theo segment
    ↓
merge/deduplicate span trên raw offsets
```

Boundary candidate:

- Q&A marker và greeting;
- canonical heading, kể cả heading giữa dòng/glued;
- article heading (`là gì`, `nguyên nhân`, `triệu chứng`, `điều trị`, `kết luận`);
- thay đổi indentation/bullet/numbering;
- subject switch (`em/cháu/bạn/mẹ/ông` ↔ `bệnh nhân/BN`);
- numbering reset/out-of-order;
- abrupt body-system/topic change;
- sentence boundary dự phòng khi newline bị collapse.

Exact/similar reuse giữa nhiều test file chỉ nên là **diagnostic cue tùy chọn**, không phải
local boundary feature cốt lõi. Dùng nó tại inference đòi batch-level comparison và có rủi ro
transductive/compliance; không triển khai trước khi xác nhận luật, và tuyệt đối không dùng known
turn-2 string/family.

### 9.3. Policy sơ bộ theo state

| State | Policy nên thử |
|---|---|
| `QUESTION` | Bắt mention sau khi resolve subject: self vs người thân/bạn bè vs generic; không đồng nhất narrator với patient |
| `DOCTOR_ANSWER` | Tách advice/generic education khỏi xác nhận chẩn đoán; có cờ `emit_generic` để A/B |
| `ARTICLE` | Bắt title/heading và list concept với high recall nếu gold annotate generic mentions; không mặc định assertion patient |
| `CLIN_HISTORY` | Dùng heading như feature cho `isHistorical`, không auto-set: bệnh mạn/thuốc đang dùng có thể vẫn ongoing; scope dừng tại seam |
| `CLIN_CURRENT` | Không kế thừa historical cue; ưu tiên symptom/onset |
| `CLIN_EVAL` | Tên/kết quả xét nghiệm, diagnosis, procedure; ghép test–result cục bộ |
| `OTHER` | Fallback extractor; không drop |

Lợi ích gần nhất không phải “model riêng cho sáu thể loại”, mà là:

1. **reset context ở seam** để cue `Tiền sử` không rò sang Q&A/article;
2. tránh Q&A answer không liên quan làm context cho **future context-aware linker/verifier**;
   linker/reranker hiện tại của repo chỉ nhận mention text nên chưa hưởng lợi trực tiếp ở bước này;
3. đưa heading/title vào window thích hợp cho boundary NER;
4. bảo toàn raw offset dù dùng shadow normalization.

### 9.4. Reuse family và consistency

Reuse family tạo hai hệ quả:

- Nếu gán nhãn turn 2 **chỉ để evaluation/model selection đúng phần được repo cho phép**, không
  train, random file split vẫn làm các fold phụ thuộc vì gần-clone; phải group theo family.
- Không force cùng toàn bộ output chỉ vì chunk giống nhau. Type/span có thể cần consistency,
  nhưng assertion, subject và linking có thể phụ thuộc context kề bên.

Ưu tiên deterministic **segment-local extraction trong từng document** để giảm ảnh hưởng của
donor context. Không triển khai cache/propagation xuyên test document khi compliance
transductive chưa được xác nhận; không pseudo-label public test và không đưa chunk test vào
training.

---

## 10. Thứ tự ablation khuyến nghị

Đây mới là đề xuất; chưa chạy experiment trong EDA này.

1. **Segment/context isolation, emit tất cả span**  
   Giữ recall policy y hệt baseline, chỉ cắt context tại seam rồi merge raw offsets. Đây là
   ablation ít rủi ro nhất để kiểm tra giá trị của segmentation.
2. **Assertion scope isolation**  
   So baseline với rule chỉ cho `isHistorical/isNegated/isFamily` nhìn trong coherent segment.
3. **Three-way Q&A pairer**  
   `matched / mismatched / unpaired`; không ép một answer làm context cho question.
4. **Generic-content emission A/B**  
   Một bản emit mọi segment; một bản suppress hoặc hạ confidence cho generic article/answer.
   Chỉ leaderboard/gold mới quyết định policy đúng.
5. **Role-specific thresholds/decoder**  
   Clinical list, narrative question, article heading và lab block có boundary prior khác nhau.
6. **Group-aware dev**  
   Khi có label evaluation hợp lệ, group 22 nontrivial family ở threshold đã chọn và coi 44
   file còn lại là singleton, tổng 66 group; threshold dependence phải được ghi trong config.

Mọi rule/segmenter phải được viết từ generic feature. Danh sách file/seam thủ công trong báo cáo
chỉ để audit, không được trở thành rule, training label hoặc lookup table.

Mỗi ablation thực sự chạy pipeline phải tạo `experiments/exp_XXXX_*` mới và cập nhật
`docs/EXPERIMENTS_LOG.md`; không ghi đè experiment cũ.

---

## 11. Điều chưa thể kết luận từ EDA này

- Không biết donor/generic block có được annotate hay không.
- Không biết redacted `***` có gold span/type hay không.
- Không thể suy score theo structure vì turn 2 không có ground truth per-file.
- Không thể dùng manual montage list làm rule inference; private test sẽ khác file ID/nội dung.
- Exact reuse chứng minh tái sử dụng bề mặt, nhưng không tự nó chứng minh nguồn sinh data cụ thể.
- Automated `layout_proxy` trong CSV chỉ là heuristic để lọc/audit; không phải taxonomy vàng.

Kết luận thực thi: **xây router theo segment là hướng đáng thử nhất từ EDA**, nhưng bước đầu phải
là context isolation và đo A/B, không phải xóa những đoạn trông “off-topic”.
