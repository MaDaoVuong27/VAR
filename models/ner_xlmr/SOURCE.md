# models/ner_xlmr — NER XLM-R (v1, iteration cũ)

Checkpoint NER **đời đầu**, đã bị [`../ner_xlmr_v2/`](../ner_xlmr_v2/SOURCE.md) thay thế —
**không experiment nào đang log dùng model này** (mọi exp_0003..0007 dùng `ner_xlmr_v2`).
Giữ lại để tham chiếu lịch sử.

Cùng công thức train với v2 (base `xlm-roberta-base`, `scripts/train_ner.py` trên
`data/synthetic/`). Cách khôi phục weight (copy tay / train lại): xem
[`../ner_xlmr_v2/SOURCE.md`](../ner_xlmr_v2/SOURCE.md), đổi `--out models/ner_xlmr`.

Weight (`model.safetensors`) gitignore như mọi model khác; chỉ config + tokenizer được track.
