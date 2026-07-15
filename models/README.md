# models — model weights / checkpoints

Nơi lưu chung các model đã tải về hoặc fine-tune (self-host, ràng buộc ≤ 9B params — xem `docs/TASK_SPEC.md`). Dùng chung giữa các experiment thay vì mỗi experiment tự giữ 1 bản copy.

```
models/
└── <tên-model>/
    ├── ... (weights — gitignored, xem .gitignore ở gốc repo)
    └── SOURCE.md    # link tải gốc (HF repo/commit) + cách tải lại, vì weight không commit vào git
```

Weight thật sự (`*.safetensors`, `*.bin`, `*.gguf`) đã bị gitignore ở mức repo — chỉ commit `SOURCE.md`/config nhỏ để người khác (hoặc BTC khi review source code) biết cách tải lại đúng model.

Mọi model dùng trong `src/` phải được liệt kê trong [`../docs/CONFIG_REFERENCE.md`](../docs/CONFIG_REFERENCE.md), trỏ tới đúng subfolder ở đây.

## Model hiện có

| Folder | Model | Vai trò | Nguồn / khôi phục |
|---|---|---|---|
| `ner_xlmr_v2/` | `xlm-roberta-base` fine-tune (~278M) | NER token-classification — **đang dùng** (exp_0003..0007) | [`ner_xlmr_v2/SOURCE.md`](ner_xlmr_v2/SOURCE.md) |
| `ner_xlmr/` | `xlm-roberta-base` fine-tune (v1) | NER đời đầu — đã bị v2 thay thế | [`ner_xlmr/SOURCE.md`](ner_xlmr/SOURCE.md) |
| `embeddings/` | cache `.npz` (SapBERT/dense) | vector KB đã encode sẵn | **gitignore toàn bộ** — tự rebuild (xem dưới) |

- **NER**: `config.json` + tokenizer track trong git; chỉ `model.safetensors` gitignore → copy tay hoặc train lại (xem SOURCE.md từng folder).
- **embeddings/**: `models/embeddings/` gitignore hoàn toàn (`*.npz` tới ~1GB). `src/normalization/sapbert.py` **tự build lại** cache khi thiếu (tải SapBERT `cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR` từ HF + encode ICD/RxNorm; cần mạng lần đầu, chậm nếu không có GPU).
- Ngân sách params (inference bản đề xuất): NER ~278M + SapBERT ~278M ≈ **556M / 9B** ✅.
