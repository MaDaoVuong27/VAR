# ground_truth — nhãn dev đã xác minh

Thư mục này chứa **nhãn ĐÃ được người xác minh** cho 15 file dev (`../input/`). `src/eval`
và `scripts/run_eval.py` chỉ chấm điểm trên các file `.json` nằm ở đây.

Hiện đang **rỗng** — chưa có file nào được xác minh.

## Workflow (đã chốt với team)

1. Nhãn **nháp** do pipeline baseline sinh ra nằm ở [`../ground_truth_draft/`](../ground_truth_draft/).
2. Mở từng file `{i}.json` bên draft, **đọc `../input/{i}.txt` và sửa lại cho đúng**:
   - thêm khái niệm bị sót, xoá khái niệm sai/thừa;
   - sửa `text`/`position` (offset ký tự trên raw, 0-indexed, `[start,end)`);
   - sửa `type`, `assertions`, `candidates` (mã ICD-10 / RxNorm đúng).
3. Lưu file đã sửa vào **thư mục này** (`ground_truth/{i}.json`).
4. Chạy `python scripts/run_eval.py` để chấm baseline trên các file đã xác minh.

## ⚠️ Vì sao không chấm thẳng trên draft

Nhãn draft = **chính output của pipeline baseline**. Nếu chấm baseline với nhãn do
chính nó sinh ra → điểm ~1.0 giả tạo (circular eval), vô nghĩa. Điểm chỉ đáng tin khi
chấm trên nhãn đã được người sửa độc lập ở thư mục này. Vì vậy `run_eval.py` cố tình chỉ
đọc `ground_truth/`, không đọc `ground_truth_draft/`.
