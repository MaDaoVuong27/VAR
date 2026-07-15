# Viettel AI Race — Medical NER + Ontology Reasoning (tiếng Việt)

Bài toán: từ văn bản y khoa tự do tiếng Việt, phát hiện & phân loại khái niệm y tế, ánh xạ `CHẨN_ĐOÁN`/`THUỐC` sang ICD-10/RxNorm, và suy luận assertion ngữ cảnh (phủ định / người nhà / tiền sử). Chi tiết đầy đủ: [`TASK/de_bai.md`](TASK/de_bai.md), [`TASK/de_bai_chi_tiet.md`](TASK/de_bai_chi_tiet.md); bản tóm tắt tra cứu nhanh: [`docs/TASK_SPEC.md`](docs/TASK_SPEC.md).

> Teammate mới hoặc AI agent (Claude Code, Codex...) làm việc trong repo này: đọc [`CLAUDE.md`](CLAUDE.md) trước — vai trò từng thư mục, quy tắc bắt buộc, và cách tương tác với `docs/`.

## Bắt đầu từ đâu

Đọc theo thứ tự trong `docs/` để nắm toàn bộ bối cảnh mà không cần đọc code:

1. [`docs/TASK_SPEC.md`](docs/TASK_SPEC.md) — đề bài rút gọn + công thức chấm điểm.
2. [`docs/IDEAS.md`](docs/IDEAS.md) — ý tưởng đang theo đuổi, ý tưởng đã thử/loại bỏ.
3. [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md) — model/tham số đang dùng trong `src/`.
4. [`docs/EXPERIMENTS_LOG.md`](docs/EXPERIMENTS_LOG.md) — bảng so sánh kết quả mọi experiment (kèm điểm thật BTC).

## Cấu trúc repo

```
TASK/               # đề bài gốc + metric (không sửa)
docs/               # tài liệu tổng hợp — đọc trước khi đọc code
knowledge_base/     # ICD-10 + RxNorm cho candidate mapping (processed/*.csv đã track; rxnorm/raw gitignore)
data/
  raw/              # input gốc từ BTC (100 file .txt của test vòng 1, không có nhãn)
  labeled/          # tập dev tự gán nhãn (input + ground_truth) để src/eval/ tự chấm điểm
  synthetic/        # dữ liệu tự sinh để train (train.jsonl / val.jsonl — đã track)
models/             # model weights/checkpoint dùng chung (weight .safetensors + embeddings gitignore)
src/                # code chính: extraction / normalization / assertion / eval / synthetic / pipeline
notebooks/          # EDA, error analysis nhanh — tách biệt code sản xuất
experiments/        # mỗi thử nghiệm 1 folder (predictions + metrics; exp_0001..0007)
references/         # code/paper SOTA về RAG, reasoning, ontology để tham khảo
scripts/            # chạy experiment, đóng gói submission, ETL knowledge base, train NER
```

## Cài đặt & tái tạo trên máy mới (đọc kỹ nếu vừa clone)

1. **Môi trường** (Python 3.10+): `pip install -r requirements.txt`. `torch` mặc định bản CPU — nếu có GPU cài bản CUDA (và đổi `faiss-cpu`→`faiss-gpu`) để chạy nhanh hơn.
2. **Có sẵn sau khi clone** (đủ để chạy pipeline + train lại): `data/raw/input/` (100 file test), `data/labeled/` (15 file gold), `data/synthetic/{train,val}.jsonl`, `knowledge_base/*/processed/*.csv`.
3. **KHÔNG có sẵn — phải bổ sung tay** (bị gitignore):
   - **NER weights** `models/ner_xlmr_v2/model.safetensors` — copy tay từ máy đã train, hoặc train lại (xem [`models/ner_xlmr_v2/SOURCE.md`](models/ner_xlmr_v2/SOURCE.md)). **Bắt buộc** để chạy bản đề xuất.
   - **Cache SapBERT** `models/embeddings/*.npz` — `src/normalization/sapbert.py` **tự build lại** lần chạy đầu (tải SapBERT từ HF + encode KB; cần mạng lần đầu, chậm nếu CPU). Copy tay để tiết kiệm thời gian.
   - **RxNorm raw** (~2.1GB) — KHÔNG cần cho pipeline (đã có `processed/`); chỉ khi build lại KB ([`knowledge_base/rxnorm/raw/SOURCE.md`](knowledge_base/rxnorm/raw/SOURCE.md)).
4. ⚠️ Lần đầu transformers tải model: đặt `HF_HUB_DISABLE_XET=1` (backend Xet trả 401).
5. **Chạy bản đề xuất nộp** (exp_0007): xem lệnh trong [`scripts/README.md`](scripts/README.md).

> ⚠️ **Bit-exact**: điểm đã log chỉ được đảm bảo y hệt khi **copy nguyên `model.safetensors`** đã train. Train lại trên GPU/driver khác (fp16 + non-determinism CUDA) cho model *tương đương* nhưng khó *y hệt*.

## Ràng buộc cần nhớ

- Nếu dùng LLM/agent: self-host, **TỔNG params mọi model local ≤ 9B**, **không gọi API ngoài**, chạy offline lúc inference.
- Output nộp bài phải do **code tự sinh, tái tạo được** — không hard-code theo input, không dùng LLM ngoài để sinh output (xem `CLAUDE.md` §Liêm chính).
- Top ~15 đội phải nộp lại source code + data + model weights + README cài đặt để BTC chạy trên private test.
