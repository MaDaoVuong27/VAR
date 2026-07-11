"""EDA + feature-tagging cho 100 file test (data/raw/input).

Chạy toàn bộ checklist trong docs/EDA_FINDINGS.md §6, gắn cờ feature cho từng
file, rồi đề xuất một tập con phủ đủ feature để gán nhãn tay (dev/eval set).

Output (UTF-8):
  notebooks/eda_outputs/feature_matrix.csv   # 1 dòng / file, mọi cờ + số đo
  notebooks/eda_outputs/eda_report.md        # tóm tắt phân bố + đề xuất chọn mẫu

Chỉ in ra stdout thông tin ASCII (tránh lỗi encoding cp1252 trên Windows).

Usage: python notebooks/eda_features.py
"""
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "raw" / "input"
OUT_DIR = ROOT / "notebooks" / "eda_outputs"

# ---------- helpers ----------

DOSAGE_RE = re.compile(r"\b\d+([.,]\d+)?\s?(mg|mcg|ml|g|iu|units?)\b", re.IGNORECASE)
DRUG_ROUTE_RE = re.compile(r"\b(po|iv|im|sc|bid|tid|qid|qd|qhs|qam|q\d+h|prn|nebs?|daily)\b", re.IGNORECASE)
LAB_TOKEN_RE = re.compile(
    r"\b(wbc|neut|lymp|lymph|hgb|hct|plt|rbc|troponin|creatinin|creatinine|"
    r"glucose|inr|alt|ast|ure|urea|bun|spo2|natri|kali|bạch cầu|tiểu cầu|"
    r"men gan|troponin|hồng cầu)\b",
    re.IGNORECASE,
)
NUM_RE = re.compile(r"\b\d+([.,]\d+)?\b")

# section / structure signals
SECTION_RE = re.compile(r"(^\s*\d\s*[.)]\s)|tiền sử|bệnh sử|lý do (nhập viện|khám)|đánh giá tại bệnh viện|triệu chứng", re.IGNORECASE | re.MULTILINE)

# history signals
HISTORY_RE = re.compile(r"tiền sử|trước khi nhập viện|thuốc trước|bệnh (lý )?(mạn|mãn) tính|trong quá khứ|tiền căn", re.IGNORECASE)

# negation cues, minus false-friends ("không xác định" / "không đặc hiệu" là tên bệnh)
NEG_RE = re.compile(r"\bkhông\b|\bchưa\b|\bâm tính\b|\(-\)|\bloại trừ\b|\bkhông có\b|\bkhông ghi nhận\b", re.IGNORECASE)
NEG_FALSE_FRIEND_RE = re.compile(r"không xác định|không đặc hiệu|không rõ|không điển hình", re.IGNORECASE)

# family cues (chủ thể là người nhà mang bệnh — siết để tránh false-positive
# như "bác sĩ gia đình", "con" trong từ khác). "gia đình" trần bị loại vì nhiễu.
FAMILY_SUBJECT_RE = re.compile(
    r"tiền sử gia đình|thành viên (trong )?gia đình|trong gia đình (có|bị)|"
    r"\bbố\b|\bmẹ\b|cha mẹ|anh trai|chị gái|em trai|em gái|di truyền|người thân",
    re.IGNORECASE,
)
FAMILY_NARRATOR_RE = re.compile(r"người nhà (kể|cho biết|nhận thấy|báo)|theo lời (kể của )?người nhà", re.IGNORECASE)

MARKDOWN_RE = re.compile(r"\*\*|^\s*\*\s|^\s*\+\s", re.MULTILINE)
NA_RE = re.compile(r"\bN/A\b")

# glue: lowercase ngay sau uppercase (camel glue) hoặc cụm lặp dính liền
CAMEL_GLUE_RE = re.compile(r"[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ][A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]")
PHRASE_REPEAT_RE = re.compile(r"(.{6,}?)\1")


def has_diacritic(tok: str) -> bool:
    return any(ord(c) > 127 for c in tok)


def analyze(text: str) -> dict:
    lines = text.splitlines()
    tokens = re.findall(r"\w+", text, re.UNICODE)
    alpha = [t for t in tokens if t.isalpha()]
    english_like = [t for t in alpha if len(t) >= 4 and t.isascii()]
    eng_ratio = len(english_like) / max(1, len(alpha))

    neg_hits = len(NEG_RE.findall(text)) - len(NEG_FALSE_FRIEND_RE.findall(text))
    fam_subject = len(FAMILY_SUBJECT_RE.findall(text))
    fam_narrator = len(FAMILY_NARRATOR_RE.findall(text))

    dosage = len(DOSAGE_RE.findall(text))
    route = len(DRUG_ROUTE_RE.findall(text))
    lab_tok = len(LAB_TOKEN_RE.findall(text))
    # kết quả xét nghiệm ~ dòng có lab token và có số
    lab_result_lines = sum(
        1 for ln in lines if LAB_TOKEN_RE.search(ln) and NUM_RE.search(ln)
    )

    camel = len(CAMEL_GLUE_RE.findall(text))
    phrase_rep = len(PHRASE_REPEAT_RE.findall(text))

    return {
        "chars": len(text),
        "lines": len(lines),
        "eng_ratio": round(eng_ratio, 3),
        "eng_count": len(english_like),
        "dosage_hits": dosage,
        "route_hits": route,
        "lab_token_hits": lab_tok,
        "lab_result_lines": lab_result_lines,
        "neg_hits": max(0, neg_hits),
        "family_subject_hits": fam_subject,
        "family_narrator_hits": fam_narrator,
        "camel_glue_hits": camel,
        "phrase_repeat_hits": phrase_rep,
        "na_hits": len(NA_RE.findall(text)),
        "markdown_hits": len(MARKDOWN_RE.findall(text)),
        "section_hits": len(SECTION_RE.findall(text)),
        "history_hits": len(HISTORY_RE.findall(text)),
    }


def flags_from(m: dict) -> dict:
    return {
        "f_short": m["chars"] < 400,
        "f_long": m["chars"] > 3000,
        "f_structured": m["section_hits"] >= 3,
        "f_freeform": m["section_hits"] < 3,
        "f_drug": (m["dosage_hits"] + m["route_hits"]) >= 2,
        "f_lab": m["lab_result_lines"] >= 2,
        "f_neg": m["neg_hits"] >= 1,
        # f_family = chủ thể người nhà mang bệnh (case tính điểm isFamily thật sự)
        "f_family": m["family_subject_hits"] >= 1,
        # f_narrator = "người nhà kể" — chỉ là nhiễu ngữ cảnh, KHÔNG tạo isFamily
        "f_narrator": m["family_narrator_hits"] >= 1,
        "f_history": m["history_hits"] >= 1,
        "f_glue": (m["camel_glue_hits"] + m["phrase_repeat_hits"]) >= 1,
        "f_codeswitch": m["eng_ratio"] >= 0.06 or m["eng_count"] >= 10,
        "f_markdown": m["markdown_hits"] >= 1,
        "f_na": m["na_hits"] >= 3,
    }


FEATURE_ORDER = [
    "f_short", "f_long", "f_structured", "f_freeform", "f_drug", "f_lab",
    "f_neg", "f_family", "f_narrator", "f_history", "f_glue", "f_codeswitch",
    "f_markdown", "f_na",
]

# feature nào là "hiếm / khó" -> ưu tiên đảm bảo có trong tập chọn
RARE_FEATURES = ["f_family", "f_narrator", "f_glue", "f_short", "f_long", "f_freeform", "f_lab", "f_codeswitch"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(INPUT_DIR.glob("*.txt"), key=lambda p: int(p.stem))
    rows = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        m = analyze(text)
        fl = flags_from(m)
        rows.append({"file": p.name, **m, **fl})

    # ----- feature_matrix.csv -----
    field_order = ["file"] + list(rows[0].keys() - {"file"})
    # keep a stable, readable column order
    measure_cols = [
        "chars", "lines", "section_hits", "history_hits", "neg_hits",
        "family_subject_hits", "family_narrator_hits", "dosage_hits", "route_hits",
        "lab_token_hits", "lab_result_lines", "camel_glue_hits", "phrase_repeat_hits",
        "eng_ratio", "eng_count", "na_hits", "markdown_hits",
    ]
    cols = ["file"] + measure_cols + FEATURE_ORDER
    with open(OUT_DIR / "feature_matrix.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    # ----- distributions -----
    feat_counts = {ft: sum(1 for r in rows if r[ft]) for ft in FEATURE_ORDER}
    lengths = sorted(r["chars"] for r in rows)

    # ----- greedy set-cover selection -> 15 files -----
    TARGET = 15
    remaining = {ft for ft in FEATURE_ORDER}
    pool = {r["file"]: {ft for ft in FEATURE_ORDER if r[ft]} for r in rows}
    selected = []

    # 1) ưu tiên phủ các feature hiếm trước
    def pick_best(weight_rare=True):
        best, best_score = None, -1
        for fname, fts in pool.items():
            if fname in selected:
                continue
            gain = fts & remaining
            score = 0
            for ft in gain:
                score += 3 if (weight_rare and ft in RARE_FEATURES) else 1
            # tie-break: ưu tiên file "đậm đặc" nhiều feature
            score = score * 100 + len(fts)
            if score > best_score:
                best, best_score = fname, score
        return best

    while remaining and len(selected) < TARGET:
        b = pick_best()
        if b is None:
            break
        selected.append(b)
        remaining -= pool[b]

    # 2) lấp đầy tới 15 bằng file đa dạng nhất (nhiều feature) + đảm bảo có cả ngắn/dài
    if len(selected) < TARGET:
        rest = sorted(
            (r for r in rows if r["file"] not in selected),
            key=lambda r: (-sum(r[ft] for ft in FEATURE_ORDER), r["chars"]),
        )
        for r in rest:
            if len(selected) >= TARGET:
                break
            selected.append(r["file"])

    # coverage của tập đã chọn
    sel_cover = Counter()
    for fname in selected:
        for ft in pool[fname]:
            sel_cover[ft] += 1

    # exemplar files cho synthetic-train (ngoài tập selected) theo từng feature
    train_templates = {}
    for ft in FEATURE_ORDER:
        ex = [r["file"] for r in rows if r[ft] and r["file"] not in selected]
        train_templates[ft] = ex[:4]

    # ----- report.md (UTF-8) -----
    lines_out = []
    lines_out.append("# EDA report — feature tagging & đề xuất chọn mẫu\n")
    lines_out.append(f"- Tổng file: {len(rows)}")
    lines_out.append(f"- Độ dài (ký tự): min={lengths[0]}, median={lengths[len(lengths)//2]}, max={lengths[-1]}\n")
    lines_out.append("## Phân bố feature (số file có feature)\n")
    lines_out.append("| feature | số file |")
    lines_out.append("|---|---|")
    for ft in FEATURE_ORDER:
        lines_out.append(f"| {ft} | {feat_counts[ft]} |")
    lines_out.append("")
    lines_out.append(f"## Tập đề xuất gán nhãn tay ({len(selected)} file) — dev/eval set\n")
    lines_out.append("Chọn bằng greedy set-cover (ưu tiên feature hiếm), phủ toàn bộ feature.\n")
    lines_out.append("| file | " + " | ".join(FEATURE_ORDER) + " |")
    lines_out.append("|" + "---|" * (len(FEATURE_ORDER) + 1))
    for fname in selected:
        r = next(x for x in rows if x["file"] == fname)
        marks = " | ".join("x" if r[ft] else "" for ft in FEATURE_ORDER)
        lines_out.append(f"| {fname} | {marks} |")
    lines_out.append("")
    lines_out.append("### Coverage của tập chọn (mỗi feature phải >=1)\n")
    lines_out.append("| feature | #file trong tập chọn |")
    lines_out.append("|---|---|")
    for ft in FEATURE_ORDER:
        lines_out.append(f"| {ft} | {sel_cover[ft]} |")
    lines_out.append("")
    lines_out.append("## Template cho synthetic TRAIN (file BTC KHÔNG dùng train — chỉ làm mẫu văn phong)\n")
    lines_out.append("Với mỗi feature, đây là các file (ngoài dev set) minh hoạ để khi sinh synthetic train phải tái tạo cùng đặc điểm:\n")
    lines_out.append("| feature | file mẫu |")
    lines_out.append("|---|---|")
    for ft in FEATURE_ORDER:
        lines_out.append(f"| {ft} | {', '.join(train_templates[ft]) or '(hết — feature này chỉ còn trong dev set)'} |")
    lines_out.append("")

    (OUT_DIR / "eda_report.md").write_text("\n".join(lines_out), encoding="utf-8")

    # ----- ASCII stdout summary -----
    print("=== feature counts (files) ===")
    for ft in FEATURE_ORDER:
        print(f"  {ft:14s} {feat_counts[ft]:3d}")
    print(f"length min/median/max: {lengths[0]}/{lengths[len(lengths)//2]}/{lengths[-1]}")
    print(f"\nselected {len(selected)} files:")
    print("  " + ", ".join(selected))
    print("\nselected coverage (must be >=1 each):")
    missing = [ft for ft in FEATURE_ORDER if sel_cover[ft] == 0]
    for ft in FEATURE_ORDER:
        print(f"  {ft:14s} {sel_cover[ft]:2d}")
    print("MISSING:", missing if missing else "none")
    print(f"\nwrote: {OUT_DIR/'feature_matrix.csv'}")
    print(f"wrote: {OUT_DIR/'eda_report.md'}")


if __name__ == "__main__":
    main()
