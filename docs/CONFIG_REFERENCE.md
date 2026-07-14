# Tổng hợp tham số / model / settings

Nguồn sự thật cho toàn bộ tham số, model, cấu hình đang dùng trong `src/`. Cập nhật **mỗi khi** thêm/đổi model hoặc tham số quan trọng — đọc file này là biết code đang chạy gì, không cần lục code.

Ràng buộc: nếu dùng LLM/agent, **TỔNG tham số mọi model local ≤ 9B** (xem [TASK_SPEC.md](TASK_SPEC.md)).

---

## Models đang sử dụng

| Module | Model | Params | Nguồn | Vai trò | File |
|---|---|---|---|---|---|
| _(baseline Tier 0)_ | KHÔNG có model ML | 0 | — | Rule/dictionary + fuzzy string | `src/extraction`, `src/normalization/kb.py` |
| **NER (Tier 1, exp_0003)** | `xlm-roberta-base` fine-tune | ~278M | HF (fine-tune trên synthetic) | Token-classification BIO 5 type, thay rule extraction | `src/extraction/ner_extractor.py`, `models/ner_xlmr_v2/` |

- Ngân sách hiện dùng lúc inference: **~278M / 9B** (chỉ NER; candidate vẫn fuzzy, assertion vẫn rule). Còn dư lớn cho SapBERT + reranker + (tùy) LLM.
- Train NER: `scripts/train_ner.py` trên `data/synthetic/` (sinh bởi `src/synthetic/`). ⚠️ **`HF_HUB_DISABLE_XET=1`** khi tải model (backend Xet trả 401).

## Tham số NER (`src/extraction/ner_extractor.py`)

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| base model | xlm-roberta-base | đa ngôn ngữ (code-switch VN-EN) |
| maxlen / stride | 256 / 48 | sliding window cho văn bản dài |
| min_conf | 0.95 | ngưỡng lọc span (cao để giảm over-predict) |
| post-process | snap biên từ + giải chồng lấn greedy theo conf + lọc stopword/rác | chống mảnh vụn |

## Retrieval / Knowledge base settings (`src/normalization/kb.py`)

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| ICD-10 source | `knowledge_base/icd10/processed/icd10_vn.csv` | match **cả 2 cột** `ten_benh_vi` + `disease_name_en` |
| RxNorm source | `knowledge_base/rxnorm/processed/rxnorm_terms.csv` | mọi TTY (IN/SCD/SBD/BN/SY...) |
| ICD scorer / threshold / top-k | `token_set_ratio` / 78 / 3 | token_set mạnh cho tên bệnh VN (span là tập con) |
| RxNorm scorer / threshold / top-k | `token_sort_ratio` / 60 / 1 | token_sort ưu tiên clinical drug đúng liều thay vì ingredient trần |
| RxNorm blocking | token chữ đầu (head token) | thu hẹp 360k dòng → block nhỏ trước khi fuzzy |

## Tham số pipeline (`src/extraction`, `src/assertion`)

| Tham số | Giá trị | Module | Ghi chú |
|---|---|---|---|
| `_MAX_WORDS` | 10 | extraction | span dài hơn → coi là câu tường thuật, bỏ |
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

_Cập nhật lần cuối: exp_0001_baseline (2026-07-11)._
