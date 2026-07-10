"""Filter RXNCONSO.RRF down to RxNorm's own vocabulary (SAB=RXNORM) as a flat CSV.

Source: knowledge_base/rxnorm/raw/rrf/RXNCONSO.RRF (RxNorm Full Monthly
Release, pipe-delimited RRF, 18 columns per row, no header).
Keeps every term type (SCD/SBD/IN/SY/PSN/BN/...) so src/normalization can
decide precedence/fuzzy-matching strategy later; only drops rows from other
source vocabularies (SNOMEDCT_US, MTHSPL, NDDF, ...) folded into the same
release, which aren't RxNorm codes themselves.

Usage: python scripts/build_rxnorm_processed.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RRF_PATH = ROOT / "knowledge_base" / "rxnorm" / "raw" / "rrf" / "RXNCONSO.RRF"
OUT_PATH = ROOT / "knowledge_base" / "rxnorm" / "processed" / "rxnorm_terms.csv"

RRF_COLUMNS = [
    "rxcui", "lat", "ts", "lui", "stt", "sui", "ispref", "rxaui", "saui",
    "scui", "sdui", "sab", "tty", "code", "str", "srl", "suppress", "cvf",
]


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    total = 0

    with open(RRF_PATH, encoding="utf-8") as f_in, \
         open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["rxcui", "tty", "code", "str", "suppress"])
        for line in f_in:
            total += 1
            fields = line.rstrip("\n").split("|")
            row = dict(zip(RRF_COLUMNS, fields))
            if row.get("sab") != "RXNORM":
                continue
            writer.writerow([row["rxcui"], row["tty"], row["code"], row["str"], row["suppress"]])
            kept += 1

    print(f"Read {total} rows, kept {kept} rows (SAB=RXNORM) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
