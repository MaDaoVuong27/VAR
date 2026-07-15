# Tổng hợp tham số / model / settings

Nguồn sự thật cho toàn bộ tham số, model, cấu hình đang dùng trong `src/`. Cập nhật **mỗi khi** thêm/đổi model hoặc tham số quan trọng — đọc file này là biết code đang chạy gì, không cần lục code.

Ràng buộc: nếu dùng LLM/agent, **TỔNG tham số mọi model local ≤ 9B** (xem [TASK_SPEC.md](TASK_SPEC.md)).

---

## Models đang sử dụng

| Module | Model | Params | Nguồn | Vai trò | File |
|---|---|---|---|---|---|
| _(baseline Tier 0)_ | KHÔNG có model ML | 0 | — | Rule/dictionary + fuzzy string | `src/extraction`, `src/normalization/kb.py` |
| **NER (Tier 1, exp_0003+)** | `xlm-roberta-base` fine-tune | ~278M | HF (fine-tune trên synthetic) | Token-classification BIO 5 type, thay rule extraction | `src/extraction/ner_extractor.py`, `models/ner_xlmr_v2/` |
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

**Ba chiến lược candidate** (cờ `scripts/run_pipeline_exp.py`): mặc định = fuzzy KB; `--sapbert` = SapBERT-only; `--hybrid` = fuzzy trước, SapBERT lấp khi rỗng. Bài học (EXPERIMENTS_LOG): SapBERT-only + abstain th=0.7 cho dev cand cao nhất (0.457); hybrid *giữ mã sai của fuzzy* nên không cứu được.

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
| text_score | 0.3 | 1 - WER (word-level), ghép concept theo type+text/position |
| assertions_score | 0.3 | Jaccard assertions trung bình theo concept (3 type có assertion) |
| candidates_score | 0.4 | Jaccard candidates, weighted `len(gold)+1`, trung bình toàn cục |

---

_Cập nhật lần cuối: exp_0007_sapbert_th07 (2026-07-14) — thêm SapBERT + NER v2._
