# ICD-10 tiếng Việt (Bộ Y tế) — raw source

Đã tải về (2026-07-10):

- `06-byt.pdf` — Thông tư số 06/2026/TT-BYT (hiệu lực từ 01/07/2026), quy định mã hoá bệnh tật/nguyên nhân tử vong theo ICD-10. Giải thích ý nghĩa 29 cột của bảng danh mục (xem ghi chú bên dưới).
- `06-byt-kem.pdf` — Phụ lục kèm theo: **bảng danh mục mã bệnh đầy đủ**, 1271 trang, đúng cấu trúc 29 cột nêu trong thông tư.

Đây là nguồn duy nhất dùng cho ICD-10 (đã quyết định không dùng ICD-10-CM/WHO song song).

## Cấu trúc 29 cột của `06-byt-kem.pdf` (theo Điều 4, `06-byt.pdf`)

Cột 1-23: dữ liệu mô tả 1 mã bệnh — quan trọng nhất:
- Cột 16: `MÃ BỆNH` (vd `A00.0`)
- Cột 17: `MÃ BỆNH KHÔNG DẤU` (vd `A000` — mã không có dấu chấm, dùng trong 1 số hệ thống HIS)
- Cột 18: `DISEASE NAME WHO 2019 (ENGLISH)`
- Cột 20: `TÊN BỆNH` (tiếng Việt — **trường chính để match với `CHẨN_ĐOÁN` trong text**)
- Cột 1-15: phân cấp chương/khối/tiểu khối/nhóm 3 ký tự (cả tiếng Việt lẫn tiếng Anh)

Cột 24-29: cờ áp dụng cho từng mã (nên giữ lại để lọc candidate hợp lệ):
- 24: không được dùng là bệnh chính
- 25: không khuyến khích dùng là bệnh chính
- 26: không được dùng vì có mã 4-5 ký tự cụ thể hơn (→ nên loại khỏi candidate nếu có mã con thay thế)
- 27: chỉ dùng để mã hoá nguyên nhân tử vong
- 28/29: chỉ có/chủ yếu có ở nữ/nam giới

## ⚠️ Lưu ý khi extract text từ PDF

`pdftotext` mặc định (không set encoding) làm **mất hết dấu tiếng Việt** trên máy đã test (VD: "Bệnh truyền nhiễm" → "Bnh truyn nhim"). Bắt buộc phải chạy với cờ `-enc UTF-8`:

```
pdftotext -enc UTF-8 -layout 06-byt-kem.pdf output.txt
```

Với `-layout`, thứ tự đọc theo dòng vẫn tương đối đúng theo từng mã bệnh, nhưng đây là bảng 29 cột nên text tuyến tính bị xáo trộn giữa các cột — cần script parse riêng (theo pattern mã bệnh dạng `[A-Z]\d{2}(\.\d)?`), không parse tay được với 1271 trang.
