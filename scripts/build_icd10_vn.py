"""Convert the Ministry of Health ICD-10 appendix PDF into a flat CSV.

Source: knowledge_base/icd10/raw/06-byt-kem.pdf (1271 pages, 29-column table
per Thong tu 06/2026/TT-BYT). Column mapping verified against the PDF's own
header row via pdfplumber (see knowledge_base/icd10/raw/SOURCE.md).

Usage: python scripts/build_icd10_vn.py
"""
import csv
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "knowledge_base" / "icd10" / "raw" / "06-byt-kem.pdf"
OUT_PATH = ROOT / "knowledge_base" / "icd10" / "processed" / "icd10_vn.csv"

COLUMNS = [
    "stt",
    "chuong_so_la_ma",
    "ma_chuong",
    "chapter_name_en",
    "ten_chuong_vi",
    "ma_khoi",
    "block_name_en",
    "ten_khoi_vi",
    "ma_tieu_khoi_cap1",
    "tieu_khoi_cap1_name_en",
    "ten_tieu_khoi_cap1_vi",
    "ma_tieu_khoi_cap2",
    "tieu_khoi_cap2_name_en",
    "ten_tieu_khoi_cap2_vi",
    "ma_nhom_3ky_tu",
    "nhom_3ky_tu_name_en",
    "ten_nhom_3ky_tu_vi",
    "ma_benh",
    "ma_benh_khong_dau",
    "disease_name_en",
    "additional_guidance_en",
    "ten_benh_vi",
    "huong_dan_bo_sung_vi",
    "flag_khong_dung_benh_chinh",
    "flag_khong_khuyen_khich_benh_chinh",
    "flag_khong_dung_co_ma_cu_the_hon",
    "flag_chi_nguyen_nhan_tu_vong",
    "flag_chi_nu",
    "flag_chi_nam",
]
assert len(COLUMNS) == 29


def clean_cell(value):
    if value is None:
        return ""
    return " ".join(value.split())


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows_out = []
    skipped_pages = []

    with pdfplumber.open(PDF_PATH) as pdf:
        total = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages):
            tables = page.find_tables()
            if not tables:
                skipped_pages.append(page_idx + 1)
                continue
            data = tables[0].extract()
            for row in data:
                if not row or len(row) != 29:
                    continue
                stt = (row[0] or "").strip()
                chuong_so_la_ma = (row[1] or "").strip()
                if not stt.isdigit():
                    continue  # header/title rows
                if not chuong_so_la_ma or chuong_so_la_ma.isdigit():
                    continue  # page-1 column-number header row ("1,2,3,...,29"): col2 is a
                    # roman numeral (I, II, ...) on real data rows, never a plain digit
                rows_out.append([clean_cell(c) for c in row])
            if (page_idx + 1) % 100 == 0:
                print(f"...{page_idx + 1}/{total} pages, {len(rows_out)} rows so far")

    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows_out)

    print(f"Done. Wrote {len(rows_out)} rows to {OUT_PATH}")
    if skipped_pages:
        print(f"Pages with no detected table ({len(skipped_pages)}): {skipped_pages}")


if __name__ == "__main__":
    main()
