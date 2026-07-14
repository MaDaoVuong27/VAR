# Tổng hợp kết quả thử nghiệm

Bảng roll-up của mọi experiment trong `experiments/`. Mỗi dòng ứng với 1 folder `experiments/exp_XXXX_<tên>/`. Chi tiết cấu hình từng experiment nằm trong `config.yaml` của folder đó; chi tiết ý tưởng đứng sau nằm trong [IDEAS.md](IDEAS.md).

Công thức nhắc lại: `final_score = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score`

> ⚠️ Điểm dev chấm trên **gold v1** (`data/labeled/ground_truth`, 15 file, assistant-annotated, **INCOMPLETE** — đếm sót occurrence, candidate best-effort). `text_score` = proxy soft-F1 (không phải WER literal). Dùng **so sánh tương đối**; điểm tuyệt đối lấy từ **submission BTC**. Baseline/NER chấm trên **cùng 15-file gold** để so công bằng.

| ID | Ngày | Mô tả ngắn | text | assert | cand | final | Nhận xét |
|---|---|---|---|---|---|---|---|
| [exp_0001_baseline](../experiments/exp_0001_baseline/) | 2026-07-11 | Tier 0: rule/dict NER + assertion rule + fuzzy candidate (0 model) | 0.328 | 0.555 | 0.207 | 0.348 | dev 15-file gold. |
| **exp_0001 — ĐIỂM THẬT BTC** | 2026-07-12 | Baseline, hệ thống BTC (100 file) | **0.192** | **0.225** | **0.096** | **0.163** | ⭐ Mốc thật 16.34/100. NER mù văn xuôi = nút thắt. |
| [exp_0002_tier1_hybrid](../experiments/exp_0002_tier1_hybrid/) | 2026-07-11 | dense MiniLM + lexical cho ICD candidate | 0.378 | 0.622 | 0.100 | 0.340 | ❌ TỆ HƠN — embedder general yếu. |
| [exp_0003_ner_xlmr](../experiments/exp_0003_ner_xlmr/) | 2026-07-14 | Tier 1: NER XLM-R fine-tune synthetic + rule assertion + fuzzy candidate; min_conf=0.95 | 0.207 | 0.621 | 0.371 | 0.397 | dev 15-file (gold INCOMPLETE → text bị phạt oan). |
| **exp_0003 — ĐIỂM THẬT BTC** | 2026-07-14 | NER Tier 1 (min_conf=0.95), BTC 100 file | **0.286** | **0.310** | **0.107** | **0.222** | ⭐ **+5.84 vs baseline (16.34→22.18)!** text +9.45, assert +8.58, cand +1.08. text TĂNG dù dev báo tụt → gold dev thiếu phạt oan recall. |
| exp_0003b — BTC A/B | 2026-07-14 | NER min_conf=**0.6** (recall cao hơn), BTC | 0.261 | 0.290 | 0.095 | 0.203 | ❌ **20.29 < 22.18** — ngưỡng thấp tệ hơn CẢ 3 thành phần. → **precision > recall**, chốt **min_conf=0.95**. |
| [exp_0004_ner_sapbert](../experiments/exp_0004_ner_sapbert/) | 2026-07-14 | NER + **SapBERT** candidate (k=1) | 0.207 | 0.621 | 0.137 | 0.303 | SapBERT sanity check ĐÚNG (hen suyễn→J45, viêm phổi→J18.9, amlodipine→308135) nhưng **dev cand không đo được** (mã gold không chắc + khớp bề mặt với fuzzy). ⚠️ Cần BTC. |
| [exp_0005_ner_hybrid](../experiments/exp_0005_ner_hybrid/) | 2026-07-14 | NER + hybrid (fuzzy trước, SapBERT lấp khi rỗng, sap_th=0.5) | 0.207 | 0.621 | 0.116 | 0.295 | dev. |
| **exp_0005 — ĐIỂM THẬT BTC** | 2026-07-14 | NER + hybrid, BTC | 0.286 | 0.310 | **0.078** | **0.210** | ❌ **21.01 < 22.18** — candidates TỤT (10.71→7.77). text/assert y hệt exp_0003. |

> ⚠️ **dev KHÔNG đo được candidate**: mã gold v1 phỏng đoán + có ô `[]`. Fuzzy vs SapBERT phải qua BTC.
>
> 🔑 **Bài học candidate (từ BTC)**: NER **over-predict** → nhiều CHẨN_ĐOÁN/THUỐC false-positive. Fuzzy **abstain** (trả rỗng cho rác) → Jaccard(rỗng,gold-rỗng)=1.0 vô hại; SapBERT th=0.5 **luôn trả mã** → bị phạt 0.0. → **abstention là lợi thế khi NER chưa sạch**. Fix: (a) nâng ngưỡng SapBERT để abstain; (b) căn bản hơn = giảm NER over-predict (synthetic v3 mật độ thấp) → cải thiện CẢ text lẫn candidate. **exp_0003 (NER+fuzzy) = 22.18 vẫn là BEST.**

| [exp_0006_hybrid_th07](../experiments/exp_0006_hybrid_th07/) | 2026-07-14 | NER + hybrid, SapBERT abstain th=0.7 (chỉ *lấp* chỗ fuzzy rỗng) | 0.207 | 0.621 | 0.312 | 0.373 | dev. |
| **exp_0006 — ĐIỂM THẬT BTC** | 2026-07-14 | NER + hybrid abstain, BTC | 0.286 | 0.310 | 0.104 | **0.221** | ~ngang 22.18 (cand 10.42 < fuzzy 10.71). Hybrid *giữ mã sai của fuzzy* cho concept thật → không cứu được. |
| [exp_0007_sapbert_th07](../experiments/exp_0007_sapbert_th07/) | 2026-07-14 | **NER + SapBERT-only abstain th=0.7 (THAY fuzzy) + tách span xuống dòng** | 0.204 | 0.634 | **0.457** | **0.434** | ⭐ **dev cand cao nhất** (fuzzy 0.371, hybrid 0.312). SapBERT gán mã đúng ngữ nghĩa (tăng lipid→E78.5, ĐTĐ típ2→E11, thận mạn→N18.9) + abstain rác. Tách span xuống dòng fix lỗi gộp 2 chẩn đoán. **Bản đề xuất nộp** — phép thử candidate quyết định. |

---

## Cách thêm 1 experiment mới vào bảng trên

1. Tạo folder `experiments/exp_XXXX_<tên-ngắn-gọn>/` (xem `experiments/README.md`).
2. Chạy pipeline, sinh `predictions/*.json`, chạy `src/eval/` để ra `metrics.json`.
3. Thêm 1 dòng vào bảng trên, link tới folder experiment.
4. Nếu experiment dẫn tới thay đổi hướng đi, cập nhật [IDEAS.md](IDEAS.md) (mục ý tưởng đã thử/loại bỏ).
