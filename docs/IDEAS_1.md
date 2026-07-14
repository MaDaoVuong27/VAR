# IDEAS_1 — Hướng A: Fine-tune NER + chuẩn hoá có học + ensemble

> Đây là 1 trong 3 hướng giải. Trang điều hướng + so sánh 3 hướng + khuyến nghị: [IDEAS.md](IDEAS.md). Hướng còn lại: [IDEAS_2.md](IDEAS_2.md) (RAG/Knowledge Graph), [IDEAS_3.md](IDEAS_3.md) (Multi-agent). Kế hoạch dữ liệu (cleaning + synthetic) dùng chung: [DATA_PLAN.md](DATA_PLAN.md).

## 0. Vì sao hướng này là XƯƠNG SỐNG (không thể bỏ)

Điểm thật baseline BTC = **16.34/100** (text 19.2, assert 22.5, cand 9.6). Phân tích lỗi cho thấy **NER recall là nút thắt gốc**: 4/100 file predict rỗng, 21/100 file ≤2 concept vì extractor rule mù văn xuôi (xem case study sample 6/8/25/93 trong `EXPERIMENTS_LOG` + `exp_0001/notes.md`).

Hệ quả then chốt của metric: **nếu không bắt được entity thì cả 3 điểm thành phần đều = 0 cho entity đó** (không có text để tính WER, không có assertion, không có candidate). → Một khối NER tốt là **điều kiện cần** cho mọi điểm số. Đây là lý do hướng A đứng trước hướng B (RAG/candidate) và C (agent): candidate 0.4 dù quan trọng nhất cũng vô nghĩa nếu NER không tìm ra khái niệm để map.

**Mục tiêu hướng A**: thay khối `src/extraction` (rule phụ thuộc cấu trúc) bằng **model NER học được**, bắt khái niệm *bất kể vị trí trong câu* — kể cả thông tin xen kẽ trong văn xuôi.

## 1. Kiến trúc NER: token classification (sequence labeling)

**Vì sao token classification, không phải LLM generate**: SOTA hiện tại (2025) cho thấy **encoder fine-tuned vẫn vượt hoặc ngang LLM seq2seq cho NER thuần**, đặc biệt về độ chính xác biên (span boundary) và tốc độ — quan trọng vì metric chấm offset ký tự chính xác. LLM để dành cho hướng C (suy luận/assertion/hard case), không phải NER lõi.

- **Đầu vào**: cả câu/đoạn (không cắt theo bullet). Model gán nhãn **BIO** cho từng token:
  `B-TRIEU_CHUNG, I-TRIEU_CHUNG, B-CHAN_DOAN, ..., O` (5 type × {B,I} + O = 11 nhãn).
- **Không cần header/bullet** — model học từ ngữ cảnh token rằng "hen suyễn" là bệnh dù nó nằm giữa câu. Đây chính là thứ rule không làm được.
- **Ánh xạ offset**: encoder token là subword → phải map ngược span subword → **offset ký tự trên raw** (dùng `offset_mapping` của fast tokenizer). Đây là chi tiết kỹ thuật bắt buộc đúng vì metric chấm theo ký tự (xem `EDA_FINDINGS.md` §2 về nhiễu token dính liền).

### Lựa chọn base model (trong ngân sách 9B TỔNG)

| Model | Params | Ghi chú |
|---|---|---|
| `XLM-RoBERTa-base/large` | 270M / 550M | Đa ngôn ngữ, mạnh cho code-switching VN-EN (data ta có 61% file code-switch). SOTA cho biết multilingual > monolingual ở medical. |
| `PhoBERT-base/large` | 135M / 370M | Chuyên tiếng Việt, mạnh ngữ pháp VN; yếu hơn với token tiếng Anh (tên thuốc). |
| `ViHealthBERT` / `ViSoBERT` | ~135M | Domain tiếng Việt; cần kiểm tra độ phủ y khoa. |

→ **Đề xuất khởi đầu: XLM-R-base** (vì code-switching nặng + tên thuốc/EN nhiều). Ngân sách tham số rất rẻ (~270M) → còn dư ~8.7B cho retrieval encoder + 1 LLM 7B ở hướng B/C. Có thể ensemble XLM-R + PhoBERT (cả 2 < 1B) mà vẫn thừa budget.

## 2. Assertion (isNegated / isFamily / isHistorical)

2 lựa chọn, đo trên dev để chọn:
- **(a) Rule giữ nguyên Tier 0** cho assertion nếu đủ tốt (assert score baseline 22.5 — không quá tệ; rule section + cue phủ định đã bắt được phần lớn isHistorical).
- **(b) Classifier riêng**: với mỗi span NER, đưa span + cửa sổ ngữ cảnh vào encoder → phân loại đa nhãn 3 assertion. Xử lý tốt phủ định trong câu ("không ghi nhận ... A, B, C" — sample 8) mà rule khó.
- **Lưu ý class imbalance**: `isFamily` cực hiếm (2/100 file). Classifier dễ bỏ qua hoàn toàn → cần weighting/oversampling, hoặc giữ rule cho riêng isFamily.

## 3. Chuẩn hoá candidate (liên kết hướng B)

NER chỉ tìm span + type. Bước map span → mã ICD/RxNorm (candidate, trọng số 0.4) thuộc **hướng B** ([IDEAS_2.md](IDEAS_2.md)) — cần retrieval có học (SapBERT-style), không phải fuzzy. Ở đây chỉ ghi: NER và candidate là 2 khối nối tiếp, NER là input của candidate.

## 4. Fine-tune: kỹ thuật & lưu ý SOTA

- **Dữ liệu train = synthetic** (bắt buộc — chỉ có 100 sample thật, lại là test không được train). Toàn bộ chiến lược sinh data ở [DATA_PLAN.md](DATA_PLAN.md). Chất lượng synthetic **quyết định** thành bại hướng này.
- **Kỹ thuật fine-tune**:
  - Encoder NER: fine-tune đầy đủ (model nhỏ, đủ VRAM RTX 3060 12GB / A100). Không cần LoRA cho encoder <1B.
  - Nếu dùng LLM cho NER/assertion (hướng C): **LoRA/QLoRA** để vừa VRAM + giữ ngân sách.
  - Về ý tưởng user nêu (GRAG — prompt tuning đưa retrieved context + question vào prompt, 2024): **kỹ thuật này thuộc RAG prompt-augmentation, không phải fine-tune NER**. Đã cũ và hợp với LLM-QA hơn là token-classification NER. Với NER encoder ta không dùng prompt tuning; với hướng LLM (C) thì in-context/retrieval-augmented prompt vẫn hữu ích nhưng nên kèm fine-tune (instruction tuning) mới ổn định.
- **Chống overfit synthetic**: synthetic dễ bị "giả" (phân phối khác test thật). Biện pháp: đa dạng hoá nguồn synthetic, giữ nhiễu thật (token dính liền, code-switch) trong synthetic (xem `data/labeled/SELECTION.md`), validate trên dev gold thật (13 file, cần verify).
- **Ensemble**: (1) multi-seed cùng model; (2) XLM-R + PhoBERT vote span; (3) encoder-NER ∪ LLM-NER (hướng C) hợp nhất theo độ tin cậy. Ensemble thường +1-3% recall.

## 5. Rủi ro & cách kiểm soát

| Rủi ro | Kiểm soát |
|---|---|
| Offset subword→char lệch (nhất là token dính liền) | Dùng fast tokenizer `offset_mapping`; test offset khớp raw như `tests/` đã làm cho baseline |
| Synthetic không giống test thật → model học sai phân phối | DATA_PLAN đa nguồn; validate dev gold thật; error analysis lặp |
| `isFamily`/`isNegated` hiếm → recall assertion kém | rule-hybrid cho class hiếm; weighting |
| Ranh giới type (span đúng, type sai) → phạt kép | train với nhiều ví dụ biên type; hậu kiểm bằng KB (thuốc phải map được RxNorm...) |

## 6. Thứ tự thực thi đề xuất (mỗi bước = 1 experiment)

1. **DATA_PLAN v1** — sinh synthetic cơ bản (entity replacement) → tập train NER đầu tiên.
2. **exp: NER XLM-R-base** fine-tune BIO → thay `src/extraction`, giữ assertion rule + fuzzy candidate → đo delta so với baseline 16.34. Kỳ vọng text + recall tăng mạnh (nhờ hết mù văn xuôi).
3. **exp: + candidate retrieval học** (hướng B, SapBERT) → đẩy cand 0.4.
4. **exp: + assertion classifier** → đẩy assert 0.3.
5. **exp: ensemble** (multi-seed/model) → chốt.

## Nguồn tham khảo (SOTA)
- Encoder vs LLM cho biomedical NER: [Do LLMs Surpass Encoders for Biomedical NER?](https://arxiv.org/pdf/2504.00664), [Named Clinical Entity Recognition Benchmark](https://arxiv.org/pdf/2410.05046)
- Vietnamese medical NER datasets: [ViMedNER](https://publications.eai.eu/index.php/inis/article/view/5221), [VietMed-NER / Medical Spoken NER](https://arxiv.org/abs/2406.13337)
