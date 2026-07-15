# models/ner_xlmr_v2 — NER token-classification (XLM-R base, fine-tuned)

Model NER **đang dùng** của pipeline (khối extraction, hướng A). Mọi experiment đã log từ
`exp_0003` trở đi (gồm `exp_0007` — bản đề xuất nộp) đều dùng checkpoint này.

| Thuộc tính | Giá trị |
|---|---|
| Base model | `xlm-roberta-base` (~278M params) — HF Hub |
| Task | Token-classification BIO, 5 type × {B,I} + O = 11 nhãn |
| Train data | `data/synthetic/train.jsonl` + `val.jsonl` (đã track trong git) |
| Train script | `scripts/train_ner.py` |
| Inference | `src/extraction/ner_extractor.py` (maxlen 256, stride 48, min_conf 0.95 khi chạy) |

## Weight bị gitignore — cách khôi phục sau khi clone

`model.safetensors` (~1.1GB) bị gitignore (xem `.gitignore` gốc). Chỉ `config.json` + tokenizer
được track. Hai cách:

1. **Copy tay** `model.safetensors` vào folder này từ máy đã train — **KHUYẾN NGHỊ** vì đảm bảo
   điểm y hệt bản đã log (train lại không đảm bảo bit-exact).
2. **Train lại**:
   ```bash
   HF_HUB_DISABLE_XET=1 python scripts/train_ner.py \
       --base xlm-roberta-base \
       --train data/synthetic/train.jsonl --val data/synthetic/val.jsonl \
       --out models/ner_xlmr_v2 --epochs 3 --bs 16 --maxlen 256
   ```
   ⚠️ `HF_HUB_DISABLE_XET=1` để tải base model (backend Xet trả 401). Train lại trên GPU/driver
   khác có thể cho model **tương đương** nhưng khó **y hệt** (fp16 + non-determinism CUDA); trên CPU
   sẽ rất chậm.

Liệt kê trong [`../../docs/CONFIG_REFERENCE.md`](../../docs/CONFIG_REFERENCE.md).
