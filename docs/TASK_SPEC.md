# Tóm tắt đề bài (bản rút gọn, dùng để tra cứu nhanh)

> Nguồn gốc đầy đủ: [`TASK/de_bai.md`](../TASK/de_bai.md), [`TASK/de_bai_chi_tiet.md`](../TASK/de_bai_chi_tiet.md). File này chỉ là bản tóm tắt phục vụ tra cứu nhanh — khi có mâu thuẫn, lấy file gốc trong `TASK/` làm chuẩn.

## Bài toán

Từ văn bản y khoa tự do tiếng Việt (ghi chú bác sĩ, giấy xuất viện, kết quả xét nghiệm, EHR...), hệ thống phải:

1. Phát hiện các khái niệm y tế + thông tin bệnh nhân trong văn bản.
2. Phân loại từng khái niệm vào 1 trong 5 nhãn.
3. Với `CHẨN_ĐOÁN` và `THUỐC`: ánh xạ sang mã chuẩn (ICD-10 / RxNorm) — trả về danh sách candidate.
4. Với `CHẨN_ĐOÁN`, `THUỐC`, `TRIỆU_CHỨNG`: xác định assertion ngữ cảnh (phủ định / người nhà / tiền sử).

## Nhãn khái niệm (`type`)

| Nhãn | Ý nghĩa | Có `candidates`? | Có `assertions`? |
|---|---|---|---|
| `TRIỆU_CHỨNG` | Triệu chứng bệnh nhân mắc phải | Không | Có |
| `TÊN_XÉT_NGHIỆM` | Tên xét nghiệm thực hiện | Không | Không |
| `KẾT_QUẢ_XÉT_NGHIỆM` | Giá trị + đơn vị kết quả xét nghiệm | Không | Không |
| `CHẨN_ĐOÁN` | Chẩn đoán của bác sĩ | Có (ICD-10) | Có |
| `THUỐC` | Tên thuốc điều trị | Có (RxNorm) | Có |

## Assertions (tối đa 3 phần tử, chỉ áp dụng cho `CHẨN_ĐOÁN`/`THUỐC`/`TRIỆU_CHỨNG`)

- `isNegated` — bị phủ định (VD: "không ho")
- `isFamily` — liên quan người nhà, không phải bệnh nhân
- `isHistorical` — thuộc tiền sử bệnh nhân

## Format 1 phần tử output

```json
{
  "text": "...",
  "position": [start, end],
  "type": "THUỐC",
  "assertions": ["isHistorical"],
  "candidates": ["308135"]
}
```

- `position`: tính theo **ký tự**, 0-indexed, `[start, end]` trên chuỗi input gốc.
- `candidates`/`assertions` chỉ xuất hiện/có ý nghĩa với các type liên quan (xem bảng trên).

## Input / Output nộp bài (vòng 1)

```text
test/input/{i}.txt   ->   output/{i}.json     (1 <= i <= 100)
```

Mỗi `{i}.json` là 1 list các object theo format ở trên.

## Metric

```
final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score
```

- **text_score**: trung bình `(1 - WER(i))` trên trường `text`, mọi sample.
- **assertions_score**: trung bình Jaccard similarity giữa tập assertions dự đoán và ground truth, mọi sample.
- **candidates_score**: Jaccard similarity trên candidates, nhưng **weighted** theo `(len(ground_truth(k)) + 1)` của từng candidate — nghĩa là sample có nhiều candidate ground-truth hơn sẽ đóng góp nhiều hơn vào điểm tổng.
- Jaccard quy ước: cả 2 tập rỗng → 1 điểm; ground truth rỗng nhưng prediction không rỗng → 0 điểm.
- **Bẫy quan trọng**: đoán đúng `text`/`position` nhưng sai `type` → bị tính là 1 khái niệm **thừa** + 1 khái niệm **thiếu** (2 lỗi), cả 3 metric đều 0 điểm cho khái niệm đó. → phân loại type sai cũng nặng như phát hiện sai vị trí.

## Ràng buộc tài nguyên

- Tự chuẩn bị compute.
- Nếu dùng LLM/agent: **bắt buộc self-host**, **không được gọi API ngoài**.
- ⚠️ **Giới hạn 9B là TỔNG tham số của TẤT CẢ model local cộng lại**, không phải mỗi model ≤9B. Ví dụ: không thể chạy đồng thời 2 model 7B (=14B); NER encoder + LLM + reranker + embedding model — tổng phải ≤9B. → phải lập "ngân sách tham số" cho cả pipeline khi chọn model.

## Ràng buộc dữ liệu / vòng loại

- Nộp nhiều lần được, **điểm cao nhất được tính**.
- ⚠️ **LIÊM CHÍNH — NGHIÊM CẤM (coi là gian lận, sẽ bị loại)**:
  1. **Hard-code output** theo input đề cho (nhét sẵn kết quả cho từng file test).
  2. Dùng **LLM mạnh / API ngoài** (Claude, Codex, GPT, Gemini...) để **suy luận/sinh ra kết quả output** — dù trực tiếp hay gián tiếp.
  3. **Người thật tự làm ra kết quả** (gán nhãn tay tập test) rồi nộp.
  - → Bản chất: **output phải do CODE tự động sinh ra**, chạy **offline**, **tái tạo được** (BTC re-run source trên private test — nếu output không tái tạo từ code = lộ gian lận).
- **Được phép**: self-host model (tổng ≤9B, xem "Ràng buộc tài nguyên") chạy **trong pipeline tự động, offline**; tự tạo thêm dữ liệu để **huấn luyện** (không phải để chép nhãn tập test); dùng LLM ngoài để **viết code** giải pháp (khác với dùng nó sinh ra output).
- Top ~15 đội phải nộp source code + data + model weights + README để BTC chạy lại trên private test.
- **Nộp cả pipeline sinh synthetic + file synthetic gốc**: nộp toàn bộ code (kể cả code sinh synthetic data) **và** file synthetic data gốc đã dùng để train + model weights. Khi BTC re-run, code sinh synthetic (có ngẫu nhiên/seed/LLM sampling) **không tái tạo y hệt** bản gốc — nên bản gốc phải được nộp kèm; code chỉ để BTC **tham khảo cách làm**. → Hệ quả: **khâu sinh synthetic cũng phải tuân luật** (self-host ≤9B, không API ngoài), vì code bị BTC review. Chi tiết: [DATA_PLAN.md](DATA_PLAN.md) §PHẦN 2.

## Nguồn tri thức cần có sẵn (chưa được BTC cung cấp trực tiếp)

- ICD-10 (mapping cho `CHẨN_ĐOÁN`)
- RxNorm (mapping cho `THUỐC`)
- Xem [`../knowledge_base/README.md`](../knowledge_base/README.md) — hiện đang là TODO, cần tìm nguồn tải về.
