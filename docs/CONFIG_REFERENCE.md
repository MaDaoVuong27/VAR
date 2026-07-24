# Tổng hợp tham số / model / settings

Nguồn sự thật cho toàn bộ tham số, model, cấu hình đang dùng trong `src/`. Cập nhật **mỗi khi** thêm/đổi model hoặc tham số quan trọng — đọc file này là biết code đang chạy gì, không cần lục code.

Ràng buộc: nếu dùng LLM/agent, **TỔNG tham số mọi model local ≤ 9B** (xem [TASK_SPEC.md](TASK_SPEC.md)).

---

## Models đang sử dụng

| Module | Model | Params | Nguồn | Vai trò | File |
|---|---|---|---|---|---|
| _(baseline Tier 0)_ | KHÔNG có model ML | 0 | — | Rule/dictionary + fuzzy string | `src/extraction`, `src/normalization/kb.py` |
| **NER (Tier 1, exp_0003..0009)** | `xlm-roberta-base` fine-tune | ~278M | HF (fine-tune trên synthetic v2) | Token-classification BIO 5 type, thay rule extraction | `src/extraction/ner_extractor.py`, `models/ner_xlmr_v2/` |
| **NER (Tier 2, exp_0010+)** | `xlm-roberta-large` fine-tune | **~560M** | HF (fine-tune trên **synthetic v3**) | Như trên, base lớn hơn + data sửa lỗi | `models/ner_xlmr_v3_large/` |
| **NER (Tier 2b, exp_0013+)** | `xlm-roberta-large` fine-tune | ~560M | HF (fine-tune trên **synthetic v4 mix**: template 6k + Qwen2.5-7B prose 2830, `data/synthetic/train_mix.jsonl`) | Như trên, thêm văn xuôi tự nhiên do LLM self-host sinh (`src/synthetic/llm_prose.py`) | `models/ner_xlmr_v4_mix/` |
| **Candidate SapBERT (Tier 1, exp_0004+)** | `cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR` | ~278M | HF | Entity linking span→mã ICD/RxNorm (thay fuzzy ở bản đề xuất nộp) | `src/normalization/sapbert.py`, cache `models/embeddings/` |

- Ngân sách inference (bản đề xuất exp_0007): NER ~278M + SapBERT ~278M ≈ **556M / 9B** ✅ (assertion vẫn rule; chưa dùng reranker/LLM). Còn dư rất lớn.
- Mọi experiment đã log (exp_0003..0007) dùng checkpoint NER **`models/ner_xlmr_v2/`**; `models/ner_xlmr/` là bản v1 cũ đã bị thay thế (xem `models/*/SOURCE.md`).
- Train NER: `scripts/train_ner.py` trên `data/synthetic/` (sinh bởi `src/synthetic/`). ⚠️ **`HF_HUB_DISABLE_XET=1`** khi tải model (backend Xet trả 401).

## Tham số NER (`src/extraction/ner_extractor.py`)

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| base model | xlm-roberta-base | đa ngôn ngữ (code-switch VN-EN) |
| maxlen / stride | 256 / 48 | sliding window cho văn bản dài |
| min_conf | 0.95 (khi chạy) | ngưỡng lọc span; **mặc định code = 0.6**, các exp truyền `--min-conf 0.95` (A/B ở exp_0003b xác nhận 0.95 > 0.6) |
| post-process | tách span xuống dòng (`_split_newlines`) + snap biên từ + giải chồng lấn greedy theo conf + lọc stopword/rác | chống mảnh vụn + fix gộp 2 chẩn đoán khác dòng |
| `split_newlines` | mặc định **True**; `--no-split-newlines` để tắt | tắt = tái lập exp_0003 (chạy trước khi hàm này ra đời). BTC: split làm **tụt** text −0.86 & assert −0.89; dev: split làm **tăng** cand. Đánh đổi chưa chốt — xem EXPERIMENTS_LOG. |

## Train NER (`scripts/train_ner.py`) — 3 điểm BẮT BUỘC cho XLM-R-large trên 12GB

| Tham số | Giá trị | Vì sao |
|---|---|---|
| `--optim adamw_bnb_8bit` | **bắt buộc** | Adam states fp32 của 560M params = **4.5GB** (model 2.2 + grad 2.2 + Adam 4.5 ≈ 9GB → OOM trên 12GB). 8-bit hạ còn **1.14GB**. ⚠️ Smoke-test bằng `GradScaler` sẽ cho số VRAM **SAI**: scale khởi đầu 65536 → gradient overflow → optimizer step bị **skip** → Adam states không được cấp phát → đo ra 4.95GB trong khi thực tế cần 10.9GB. |
| `--bs 8 --grad-accum 2` | effective batch 16 | bs=16 trực tiếp → OOM |
| `--stride 48` + sliding window | **bắt buộc** | Trước đây `encode()` chỉ `truncation=True` (không overflow) → doc dài hơn maxlen bị **cắt cụt**, mất nhãn phía sau + lệch với inference (vốn CÓ sliding window). Với synthetic v3 (~400 token > 256) bug này ăn mất **45.7% nhãn**. |
| `warmup_ratio` / `load_best_model_at_end` | 0.1 / True | không warmup → XLM-R-large dễ collapse. Trước đây `save_strategy="no"` → val chỉ in số cho vui, model lưu ra luôn là epoch cuối. |

⚠️ **val F1 ≈ 0.9998 là VÔ NGHĨA** để đánh giá năng lực thật: `val.jsonl` sinh từ **cùng `generate.py`** với train (chỉ khác seed) → nó đo "model có học thuộc template không", không đo generalization sang bệnh án thật. Thước đo thật chỉ có dev (15 file thật) và BTC.

`--mask-prob` (mặc định 0.0 = tắt, hành vi cũ): whole-entity masking kiểu OpenBioNER, che **toàn
bộ token** của 1 entity bằng `[MASK]` lúc train (không áp cho val) để ép model dùng ngữ cảnh thay
vì học thuộc mặt chữ. **Đã A/B trên `train_v5c` (exp_0030, xem EXPERIMENTS_LOG.md): p=0.1 tín hiệu
trái chiều (candidates tốt hơn, assertions tệ hơn, final thấp hơn), p=0.3 tệ mọi mặt → KHÔNG bật
mặc định, giữ 0.0 cho mọi checkpoint đang dùng.**

## Retrieval / Knowledge base settings — fuzzy (`src/normalization/kb.py`)

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| ICD-10 source | `knowledge_base/icd10/processed/icd10_vn.csv` | match **cả 2 cột** `ten_benh_vi` + `disease_name_en` |
| RxNorm source | `knowledge_base/rxnorm/processed/rxnorm_terms.csv` | mọi TTY (IN/SCD/SBD/BN/SY...) |
| ICD scorer / threshold / top-k | `token_set_ratio` / 78 / 3 | token_set mạnh cho tên bệnh VN (span là tập con) |
| RxNorm scorer / threshold / top-k | `token_sort_ratio` / 60 / 1 | token_sort ưu tiên clinical drug đúng liều thay vì ingredient trần |
| RxNorm blocking | token chữ đầu (head token) | thu hẹp 360k dòng → block nhỏ trước khi fuzzy |

## Retrieval SapBERT — entity linking Tier 1 (`src/normalization/sapbert.py`)

Dùng từ exp_0004; **bản đề xuất nộp (exp_0007)** dùng SapBERT-only (thay fuzzy) + abstain.

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| Model | `cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR` | ~278M, cross-lingual (nền XLM-R base), self-align trên UMLS |
| Pooling / max_length | CLS token / 32 | tên khái niệm ngắn |
| Index | FAISS `IndexFlatIP` trên embedding chuẩn hoá (= cosine) | ICD (cột VN+EN) + RxNorm (mọi TTY) |
| Cache | `models/embeddings/sapbert_{icd,rxn}.npz` | **gitignore**; `build()` tự tạo khi thiếu (encode lại KB) |
| threshold (abstain) | **0.7** (exp_0007) | sim < th → trả rỗng (abstain) thay vì gán mã sai → tránh phạt Jaccard 0 |
| top-k | 1 (ICD & RxNorm) | gold thường 1 mã/khái niệm |

**Bốn chiến lược candidate** (cờ `scripts/run_pipeline_exp.py`): mặc định = fuzzy KB; `--sapbert` = SapBERT-only; `--hybrid` = fuzzy trước, SapBERT lấp khi rỗng; `--reranker <model>` = SapBERT retrieval (giữ nguyên threshold/abstain) + cross-encoder rerank top-k. Bài học (EXPERIMENTS_LOG): SapBERT-only + abstain th=0.7 thắng fuzzy/hybrid dứt khoát trên BTC (exp_0007: cand 16.17 vs fuzzy 10.71).

## Reranker — SapBERT retrieval + cross-encoder (`src/normalization/reranker.py`, exp_0018+)

**🏆 Cấu hình BEST hiện tại (exp_0022, BTC 32.79790)**:
```
python scripts/run_pipeline_exp.py --exp <tên> --ner models/ner_xlmr_v4_mix --min-conf 0.95 \
  --reranker BAAI/bge-reranker-v2-m3 --sap-th 0.7 --assertion-clf models/assertion_xlmr
```
⚠️ **KHÔNG dùng rule** (mặc định khi bỏ `--assertion-clf`) — xem cảnh báo dưới về đảo ngược classifier vs rule. `min_conf` đã quét lại 0.80-0.99 trên nền classifier: PHẲNG (0.80-0.95 đều ~0.397-0.398 dev, trong biên độ nhiễu) → giữ 0.95, không có tín hiệu đổi.

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| Retrieval | SapBERT gốc, top-10, threshold=0.7 | KHÔNG đổi so với `SapBertMatcher` — abstain vẫn do threshold này quyết định |
| Reranker | `BAAI/bge-reranker-v2-m3` (~568M) | **off-the-shelf, KHÔNG fine-tune** — cache sẵn HF, cross-encoder tổng quát đa ngôn ngữ |
| Cơ chế | Rerank chỉ đổi **thứ tự trong tập đã qua threshold** | Không đụng abstain rate (verify: 22%=22% giữa exp_0013 và exp_0018) |
| Kết quả BTC | cand 23.16→23.47 (+1.3%), final +0.12 | Cải tiến NHỎ — xem EXPERIMENTS_LOG §exp_0018 để hiểu vì sao dev báo sai hướng cho ca này |

⚠️ **2 lần fine-tune SapBERT riêng (contrastive) đã THẤT BẠI** trên dev, không nộp BTC — xem `scripts/finetune_sapbert.py` + EXPERIMENTS_LOG §exp_0016/0017 (naive & hard-negative, cả hai đều làm cand tụt trên dev vì contrastive loss dịch chuyển toàn phổ similarity, threshold 0.7 mất hiệu lực).

📌 Trên **test turn 2** (BTC cấp lại 2026-07-23), cấu hình BEST ở trên (`ner_xlmr_v4_mix` + boundary-fix
inference-time trong `ner_extractor.py`) = `exp_0026`, BTC thật **final 22.7685** (WER 72.17, J_assert
30.33, J_cand 13.30) — anchor mới để so sánh trên test hiện hành (thay `exp_0022`=32.798 đo trên test cũ,
xem EXPERIMENTS_LOG §turn2).

`RerankMatcher(use_description=...)`: đã thêm tuỳ chọn cho reranker "ăn" **mô tả KB** (phân cấp
ICD + đồng nghĩa RxNorm, rule-based 100%, `build_icd_descriptions()`/`build_rxnorm_descriptions()`)
thay tên trần, kỳ vọng giúp disambiguate tốt hơn (hướng OpenBioNER). **Đã thử + loại bỏ** (exp_0028/
0029, xem EXPERIMENTS_LOG): mô tả dài làm loãng tín hiệu relevance của cross-encoder off-the-shelf,
dev candidates_score tệ hơn ở cả `max_length=64` (0.3011) và `max_length=160` (0.2903) so với tên
trần (0.3333). **Default đã revert về `use_description=False`** — không đổi hành vi cấu hình BEST
ở trên.

## Assertion classifier (`src/assertion/classifier.py`, exp_0022+) — THẮNG RULE trên BTC dù dev nói ngược

🔴 **Đảo ngược quan trọng**: dev báo classifier (0.6365) THUA rule gốc (0.6607); BTC báo NGƯỢC LẠI — classifier (J_assertion 39.3464) thắng đậm rule vá (36.6015) lẫn rule gốc (36.3798). Chi tiết + giả thuyết nguyên nhân (rule bị fit theo đúng dev sample dùng để chẩn đoán bug): EXPERIMENTS_LOG §ĐẢO NGƯỢC LỚN.

| Thành phần | Giá trị |
|---|---|
| Base | `xlm-roberta-base` fine-tune, đa nhãn (3 sigmoid: isNegated/isFamily/isHistorical) |
| Train data | 80k template + 14k prose (`data/synthetic/train.jsonl` + `prose.jsonl`) |
| Kiến trúc | span đánh dấu `[ENT]...[/ENT]`, cửa sổ ngữ cảnh 180 trước/80 sau |
| Model | `models/assertion_xlmr/` |
| Cờ | `--assertion-clf models/assertion_xlmr` |

⚠️ **Bài học**: đừng tin dev khi so "rule vá theo quan sát lỗi trên dev" vs "model train trên data lớn" — dù cùng span/NER. Quy luật "cùng span → dev tin được" chỉ áp dụng an toàn cho candidates (matcher), KHÔNG áp dụng chắc chắn cho lựa chọn rule-vs-model của assertion.

⚠️ **Ngân sách 9B nếu dùng reranker lúc inference**: NER 560M + SapBERT 278M + bge-reranker-v2-m3 **568M** ≈ **1.4B/9B** — vẫn dư rất lớn, nhưng nếu muốn margin rộng hơn theo đúng đề xuất gốc IDEAS_2 thì thay bằng mMiniLM ~118M (chưa fine-tune, chưa test).

_(`src/normalization/dense.py` = dense off-the-shelf của exp_0002, đã LOẠI — không dùng trong bản nộp.)_

## Tham số pipeline (`src/extraction`, `src/assertion`)

| Tham số | Giá trị | Module | Ghi chú |
|---|---|---|---|
| `_MAX_WORDS` | 10 | extraction | span dài hơn → coi là câu tường thuật, bỏ (áp cho rule extractor) |
| section bỏ qua | narrative / procedure / imaging | extraction | ưu tiên precision (bỏ văn xuôi) |
| drug detection | route-word OR drug_vocab, loại lab-word | extraction | tránh bắt nhầm "creatinine" (ingredient RxNorm) |
| isHistorical | section=history OR cue tiền sử trong dòng | assertion | |
| isNegated | cue phủ định trong `[đầu dòng, hết span]`, lọc false-friend | assertion | |
| isFamily | cue chủ thể người nhà, loại narrator | assertion | conservative |

## Metric (`src/eval/metric.py`)

| Điểm | Trọng số | Cách tính (giả định, xem docstring metric.py) |
|---|---|---|
| text_score | 0.3 | proxy soft-F1 trên cặp đã ghép / `max(#gold,#pred)` — **không phải** 1−WER literal (WER-with-insertion bị floor về 0, vô dụng để so sánh) |
| assertions_score | 0.3 | Jaccard assertions trung bình theo concept (3 type có assertion) |
| candidates_score | 0.4 | Jaccard candidates, weighted `len(gold)+1`, trung bình toàn cục |
| ghép pred↔gold | — | greedy 1-1, **bắt buộc cùng type**, khớp text chuẩn hoá HOẶC IoU(position) > 0.5 |

⚠️ **Quy tắc concept không ghép được (sửa 2026-07-15)**: gold bỏ sót **và** pred thừa đều = **0 điểm** cho assertions/candidates — KHÔNG áp `J(∅,∅)=1`. Quy ước `J(∅,∅)=1` chỉ dành cho concept **có thật, đã ghép** mà gold không có mã. Concept thừa vẫn vào mẫu số (`w=1`). Trước bản sửa, mỗi concept rác abstain được +1.0 → dev cand thổi phồng ~3.5×. Lịch sử + bằng chứng: §"Lỗi metric đã sửa" trong [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md).

Chấm lại mọi exp từ predictions đã lưu (không cần model weights): `python scripts/rescore_all.py [--write]`.

---

_Cập nhật lần cuối: 2026-07-15 — sửa lỗi metric (concept không ghép = 0 điểm) + chấm lại toàn bộ exp; thêm `scripts/rescore_all.py`._
