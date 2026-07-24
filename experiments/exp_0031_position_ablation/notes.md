# exp_0031 — Position ablation: `position` field có thực sự quan trọng không?

## Câu hỏi
Lấy y nguyên output đạt điểm BTC thật cao nhất hiện tại (`exp_0026_v4mix_turn2`, final 22.7685),
ghi đè **toàn bộ** field `position` của mọi concept thành `[0, 0]`, giữ nguyên `text`/`type`/
`candidates`/`assertions`. Hỏi: điểm giảm bao nhiêu?

## Vì sao có thể trả lời một phần mà không cần nộp
Cơ chế ghép predict↔gold trong `src/eval/metric.py::_match()`:
```
cùng type BẮT BUỘC, rồi:
  - text chuẩn hoá trùng khớp tuyệt đối  -> match (ưu tiên)
  - ngược lại: position IoU > 0.5        -> match (fallback)
  - cả hai đều fail                       -> không match (pred thừa + gold thiếu)
```
→ Khi `position=[0,0]` toàn bộ, fallback IoU **luôn hỏng** (trừ khi gold cũng nằm ở [0,0], không
xảy ra thực tế) — chỉ những concept **text khớp tuyệt đối** mới còn được ghép. Đây chính là điều
cần đo: bao nhiêu % điểm hiện tại đến từ text-match thuần vs. từ fallback vị trí.

## Đo trên dev (data/labeled/ground_truth, gold thật — số tin được)

| | gốc (exp_0026) | position=[0,0] | delta |
|---|---|---|---|
| text_score | 0.2577 | 0.2340 | **−0.0237** |
| assertions_score | 0.6328 | 0.6318 | −0.0010 (gần như không đổi) |
| candidates_score | 0.3333 | 0.3191 | **−0.0142** |
| final_score | 0.4005 | 0.3874 | **−0.0131 (−3.3% tương đối)** |

**Diễn giải**:
- `assertions_score` gần như không đổi — hợp lý, vì Jaccard(assertions) tính trên concept ĐÃ ghép
  theo type+index cố định trong pipeline hiện tại (không phụ thuộc lại vào matcher `_match()` theo
  cùng cách text/candidates dùng để tính WER/Jaccard-candidates), nên ít nhạy với việc ghép lại.
- `text_score`/`candidates_score` giảm nhẹ nhưng KHÔNG sập — nghĩa là phần lớn các cặp predict↔gold
  đã khớp qua **text chuẩn hoá trùng khớp tuyệt đối**, chỉ một thiểu số dựa vào fallback IoU vị trí
  để được ghép. → **Position đóng vai trò phụ, không phải xương sống của điểm số trong scorer nội
  bộ (proxy) của ta.**

## ĐÃ NỘP — kết quả BTC thật (2026-07-24), khác HẲN dự đoán từ dev proxy

| | exp_0026 (position thật) | exp_0031 (position=[0,0]) | delta |
|---|---|---|---|
| WER | 72.1682 | **100** (mismatch TOÀN BỘ) | +27.83 (tệ hơn) |
| J_assertion | 30.33 | **0** | −30.33 |
| J_candidates | 13.2999 | 19.33 | **+6.03 (TĂNG, bất ngờ)** |
| final | **22.7685** | **~7.73** | **−15.04 (−66% tương đối)** |

**Dev proxy đã dự đoán SAI HƯỚNG ĐỘ LỚN**: dev nói −3.3%, BTC thật −66%. Đây là bằng chứng RÕ RÀNG
rằng scorer BTC thật xử lý `position` **rất khác** với giả định lỏng lẻo trong `_match()` của
`src/eval/metric.py` (text-match OR position-IoU>0.5). Với `position=[0,0]` toàn bộ, thực tế
**gần như KHÔNG concept nào được ghép** — `WER=100` (mọi word đều tính là chèn/xoá, y hệt như
không đoán được gì) và `J_assertion=0` (mọi gold concept coi như "missed", pred=∅, phần lớn gold có
assertion non-empty → J=0). → **Kết luận: BTC's matcher thật gần như BẮT BUỘC dựa vào `position` để
ghép cặp predict↔gold, không đơn thuần là fallback phụ như model nội bộ của ta giả định.**

**Điểm bất ngờ**: `J_candidates` lại TĂNG (13.30→19.33) chứ không giảm. Giả thuyết: khi hầu như mọi
pred bị coi là "concept thừa" (unmatched), các pred có `candidates=[]` (abstain — vốn NHIỀU trong
cấu hình reranker sap_th=0.7) vẫn ăn `J(∅,∅)=1` theo đúng quy ước abstain đã kiểm chứng nhiều lần
(xem `EXPERIMENTS_LOG.md` §exp_0012) — cơ chế "abstain sinh điểm ảo" áp dụng CẢ KHI concept đó thực
ra đã bị predict đúng nhưng mất credit vì sai position. Đây là hệ quả phụ, không phải bằng chứng
position "ít quan trọng" cho candidates — WER/J_assertion đã cho thấy rõ ràng position là bắt buộc.

**Ý nghĩa cho hướng đi tiếp theo**: việc đầu tư vào ĐỘ CHÍNH XÁC BOUNDARY của NER (các fix
`_snap_word`/`_trim_narrative_paren` ở `exp_0024`, `diagnose_boundary.py` làm công cụ chẩn đoán
chính) có giá trị THẬT SỰ CAO hơn những gì dev proxy từng cho thấy — vì matcher BTC thật có vẻ
nhạy với vị trí hơn nhiều so với model nội bộ. Đã ghi thành cảnh báo trong
`src/eval/metric.py` docstring và `docs/IDEAS.md`.

## Không train lại gì
Không đổi NER/reranker/assertion model — chỉ hậu xử lý field `position` trên output JSON đã có sẵn
của `exp_0026`. Chi phí gần như 0 compute, nhưng phát hiện có giá trị lớn cho hiểu biết về scorer.
