# EDA report — feature tagging & đề xuất chọn mẫu

- Tổng file: 100
- Độ dài (ký tự): min=136, median=1229, max=4428

## Phân bố feature (số file có feature)

| feature | số file |
|---|---|
| f_short | 13 |
| f_long | 3 |
| f_structured | 99 |
| f_freeform | 1 |
| f_drug | 15 |
| f_lab | 18 |
| f_neg | 82 |
| f_family | 2 |
| f_narrator | 2 |
| f_history | 93 |
| f_glue | 27 |
| f_codeswitch | 61 |
| f_markdown | 2 |
| f_na | 1 |

## Tập đề xuất gán nhãn tay (15 file) — dev/eval set

Chọn bằng greedy set-cover (ưu tiên feature hiếm), phủ toàn bộ feature.

| file | f_short | f_long | f_structured | f_freeform | f_drug | f_lab | f_neg | f_family | f_narrator | f_history | f_glue | f_codeswitch | f_markdown | f_na |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.txt |  | x | x |  |  | x | x |  |  | x | x | x | x | x |
| 31.txt | x |  |  | x |  |  | x |  |  |  | x | x |  |  |
| 84.txt |  |  | x |  |  | x | x | x |  | x |  | x |  |  |
| 87.txt |  |  | x |  |  |  | x |  | x | x | x | x |  |  |
| 36.txt |  |  | x |  | x | x | x |  |  | x |  | x | x |  |
| 82.txt |  |  | x |  | x | x | x |  |  | x | x | x |  |  |
| 51.txt |  |  | x |  | x | x | x |  |  | x | x | x |  |  |
| 37.txt |  |  | x |  | x | x | x |  |  | x | x | x |  |  |
| 70.txt |  |  | x |  | x | x | x |  |  | x | x | x |  |  |
| 91.txt |  |  | x |  |  | x | x |  |  | x | x | x |  |  |
| 97.txt |  |  | x |  | x | x | x |  |  | x |  | x |  |  |
| 66.txt |  |  | x |  |  | x | x |  |  | x | x | x |  |  |
| 35.txt |  |  | x |  |  | x | x |  |  | x | x | x |  |  |
| 50.txt |  |  | x |  | x |  | x |  |  | x | x | x |  |  |
| 54.txt |  |  | x |  |  | x | x |  |  | x | x | x |  |  |

### Coverage của tập chọn (mỗi feature phải >=1)

| feature | #file trong tập chọn |
|---|---|
| f_short | 1 |
| f_long | 1 |
| f_structured | 14 |
| f_freeform | 1 |
| f_drug | 7 |
| f_lab | 12 |
| f_neg | 15 |
| f_family | 1 |
| f_narrator | 1 |
| f_history | 14 |
| f_glue | 12 |
| f_codeswitch | 15 |
| f_markdown | 2 |
| f_na | 1 |

## Template cho synthetic TRAIN (file BTC KHÔNG dùng train — chỉ làm mẫu văn phong)

Với mỗi feature, đây là các file (ngoài dev set) minh hoạ để khi sinh synthetic train phải tái tạo cùng đặc điểm:

| feature | file mẫu |
|---|---|
| f_short | 15.txt, 22.txt, 26.txt, 29.txt |
| f_long | 20.txt, 41.txt |
| f_structured | 1.txt, 2.txt, 4.txt, 5.txt |
| f_freeform | (hết — feature này chỉ còn trong dev set) |
| f_drug | 1.txt, 20.txt, 27.txt, 33.txt |
| f_lab | 5.txt, 17.txt, 38.txt, 40.txt |
| f_neg | 1.txt, 2.txt, 4.txt, 5.txt |
| f_family | 77.txt |
| f_narrator | 23.txt |
| f_history | 1.txt, 2.txt, 4.txt, 5.txt |
| f_glue | 4.txt, 24.txt, 32.txt, 47.txt |
| f_codeswitch | 1.txt, 4.txt, 5.txt, 6.txt |
| f_markdown | (hết — feature này chỉ còn trong dev set) |
| f_na | (hết — feature này chỉ còn trong dev set) |
