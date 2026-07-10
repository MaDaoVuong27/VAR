# RxNorm — raw source

Tải về đây, giữ nguyên cấu trúc giải nén.

## Cách tải

1. Đăng ký tài khoản UTS miễn phí: https://uts.nlm.nih.gov/uts/signup-login
2. Đăng nhập, tải **RxNorm Full Monthly Release** tại: https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html
3. Giải nén zip **trực tiếp vào folder này** (`knowledge_base/rxnorm/raw/`) — kết quả nên có dạng:

```
knowledge_base/rxnorm/raw/
└── rrf/
    ├── RXNCONSO.RRF   # quan trọng nhất — tên thuốc + hàm lượng + mã RxCUI
    ├── RXNREL.RRF
    ├── RXNSAT.RRF
    └── ... (các file .RRF khác)
```

## Ghi chú

- File `.RRF` bị gitignore (nặng, re-download được) — chỉ file này (`SOURCE.md`) được track trong git.
- Chỉ cần `RXNCONSO.RRF` ở cấp **SCD/SBD (clinical drug)** để xây `processed/` — xem `../../README.md`.
