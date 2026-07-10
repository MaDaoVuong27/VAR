# Knowledge Base — ICD-10 & RxNorm

Nguồn tri thức tĩnh dùng để ánh xạ (`candidates`) cho `CHẨN_ĐOÁN` (ICD-10) và `THUỐC` (RxNorm). Đề bài không cung cấp sẵn 2 bộ này — cần tự tìm/tải.

## Nguồn tải (đã khảo sát — xem thảo luận trong `docs/IDEAS.md`)

### RxNorm

- Đăng ký tài khoản UTS miễn phí: https://uts.nlm.nih.gov/uts/signup-login (license UMLS, duyệt gần như ngay).
- Tải **RxNorm Full Monthly Release** tại https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html — zip chứa các file `.RRF` (pipe-delimited).
- File quan trọng nhất: `RXNCONSO.RRF` — mỗi RxCUI có nhiều dòng theo `TTY` (IN/PIN=ingredient, SCD/SBD=clinical drug đầy đủ hàm lượng+dạng bào chế, SY/PSN=tên đồng nghĩa/tên kê đơn...). **Giữ mọi TTY** (không lọc riêng SCD/SBD) để tối đa recall khi fuzzy-match — `processed/rxnorm_terms.csv` đã lọc theo hướng này.
- Thuốc trong text tiếng Việt thường vẫn viết tên hoạt chất gốc (Latin/English) → dùng trực tiếp RxNorm tiếng Anh, không cần dịch.
- ⚠️ Đã kiểm tra: mã ví dụ trong đề (`360047` cho "Chlorpheniramine 0.4 MG/ML") **không tồn tại** trong bản RxNorm Full Release mới nhất (07/06/2026) — RxCUI có thể đã bị retire/remap giữa các lần release. Không nên coi các mã ví dụ trong đề là "phải khớp tuyệt đối" khi tự đánh giá — ưu tiên đúng cấu trúc/logic mapping hơn là khớp y hệt 1 RxCUI cụ thể đã lỗi thời.

### ICD-10 — chỉ dùng bản tiếng Việt của Bộ Y tế (đã quyết định, không dùng ICD-10-CM/WHO song song)

- Nguồn: Thông tư 06/2026/TT-BYT (hiệu lực 01/07/2026) — tên bệnh tiếng Việt ↔ mã ICD-10, dùng thực tế tại bệnh viện VN. Giải quyết trực tiếp bài toán matching tiếng Việt → mã, không cần cross-lingual embedding.
- **Đã tải xong** (2026-07-10): `icd10/raw/06-byt.pdf` (thông tư, giải thích cấu trúc bảng) + `icd10/raw/06-byt-kem.pdf` (phụ lục — bảng danh mục đầy đủ, 1271 trang, 29 cột). Chi tiết cấu trúc cột + lưu ý quan trọng khi extract text: xem [`icd10/raw/SOURCE.md`](icd10/raw/SOURCE.md).

## TODO còn lại

- [x] Tải ICD-10 (Bộ Y tế) — xong.
- [x] Tải RxNorm Full Release — xong, giải nén tại `rxnorm/raw/rrf/`.
- [x] Lọc `rxnorm/raw/rrf/RXNCONSO.RRF` (`SAB=RXNORM`, mọi TTY) → `rxnorm/processed/rxnorm_terms.csv` (362,409 dòng). Script: `scripts/build_rxnorm_processed.py`.
- [x] Parse `icd10/raw/06-byt-kem.pdf` (29 cột, dùng `pdfplumber`) → `icd10/processed/icd10_vn.csv` (15,844 dòng, đã validate: STT liên tục, không trùng mã, encoding đúng). Script: `scripts/build_icd10_vn.py`.
- [ ] Quyết định chiến lược retrieval (lexical/BM25, dense embedding, hybrid) — ghi vào `docs/CONFIG_REFERENCE.md` khi chốt.

## Cấu trúc thư mục

```
knowledge_base/
├── icd10/
│   ├── raw/             # 06-byt.pdf + 06-byt-kem.pdf — track trong git (~22MB, ổn)
│   └── processed/       # icd10_vn.csv — 29 cột: mã bệnh, tên bệnh VN/EN, cờ 24-29 — track trong git
└── rxnorm/
    ├── raw/             # RxNorm Full Release giải nén (rrf/, prescribe/, scripts/) — GITIGNORE (~2.1GB, xem SOURCE.md)
    └── processed/       # rxnorm_terms.csv — rxcui, tty, code, str, suppress (SAB=RXNORM, 362,409 dòng) — track trong git
```

### Quy tắc git khác nhau giữa 2 nguồn (quan trọng, đọc trước khi clone/push)

- **ICD-10 raw** (`icd10/raw/06-byt.pdf`, `06-byt-kem.pdf`, ~22MB) — **được track trong git bình thường**, không gitignore. Nhỏ, không vấn đề gì.
- **RxNorm raw** (`rxnorm/raw/`, ~2.1GB) — **gitignore**, không track. Lý do: 7 file `.RRF`/`.zip` vượt quá 100MB (giới hạn cứng của GitHub, push sẽ bị từ chối), tổng dung lượng ~2.1GB không hợp lý để đưa vào git history. Muốn có raw này, tự tải theo hướng dẫn trong [`rxnorm/raw/SOURCE.md`](rxnorm/raw/SOURCE.md) (tài khoản UMLS free, ~5-10 phút) — **không cần thiết cho việc chạy pipeline hàng ngày**, vì `processed/rxnorm_terms.csv` (25MB, đã track trong git) đã đủ dùng.
- Cả 2 `processed/*.csv` đều được track trong git — đây là dữ liệu thật mà `src/normalization` dùng, teammate pull code về là chạy được ngay, không cần tải/build lại gì.

## Ghi chú

- RxNorm giữ **mọi TTY** (không chỉ SCD/SBD) trong `processed/rxnorm_terms.csv` để tối đa recall khi fuzzy-match.
- Với ICD-10, 1 chẩn đoán có thể map nhiều mã (VD ví dụ đề bài: "trào ngược dạ dày - thực quản" → `K21.0`, `K21.9`) → retrieval nên trả về top-k, không chỉ 1 mã.
