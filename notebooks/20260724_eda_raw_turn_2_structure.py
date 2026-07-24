"""Deep structural EDA for the 100 unlabeled raw_turn_2 documents.

This script deliberately separates three axes which are easy to conflate:

1. semantic genre: clinical record, health-education article, consultation Q&A;
2. physical layout: clinical numbered template, numbered article, dialogue,
   narrative case, compacted/fragmentary text, or a residual hybrid;
3. corruption/stitching signals: redaction, missing newlines, glued headings,
   duplicated material, cross-document reuse, and mixed high-precision genres.

The labels are heuristic EDA features, not ground truth and not training labels.
No file ID is used as a feature. The script only reads competition inputs and
writes aggregate/feature artifacts under notebooks/eda_outputs/.

Usage:
    python notebooks/20260724_eda_raw_turn_2_structure.py

Outputs:
    notebooks/eda_outputs/turn2_structure_features.csv
    notebooks/eda_outputs/turn2_reuse_pairs.csv
    notebooks/eda_outputs/turn2_repeated_lines.csv
    notebooks/eda_outputs/turn2_structure_summary.json
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "raw_turn_2" / "input"
OUTPUT_DIR = ROOT / "notebooks" / "eda_outputs"

TOKEN_RE = re.compile(r"\w+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")

BULLET_LINE_RE = re.compile(r"^\s*(?:[•●▪◦‣*+-]|–|—)\s+")
UNICODE_BULLET_RE = re.compile(r"[•●▪◦‣]")
NUMBERED_LINE_RE = re.compile(r"^\s*(\d{1,2})\s*[.)]\s*(.+?)\s*$")
SHORT_NUMBERED_HEADING_RE = re.compile(
    r"^\s*(\d{1,2})\s*[.)]\s*(.{1,140}?)\s*$"
)

QUESTION_LABEL_RE = re.compile(
    r"(?im)^\s*(?:"
    r"câu\s+hỏi(?:\s+(?:của|từ)\s+người\s+dùng)?"
    r"(?:\s+gửi\s+đến\s+hệ\s+thống)?|hỏi"
    r")\s*(?::|$)"
)
ANSWER_LABEL_RE = re.compile(
    r"(?im)^\s*(?:câu\s+trả\s+lời\s+của\s+bác\s+sĩ|"
    r"bác\s+sĩ\s+trả\s+lời|trả\s+lời)"
    r"\s*(?::|$)"
)
DOCTOR_GREETING_RE = re.compile(
    r"(?i)\b(?:chào\s+(?:bạn|bác\s+sĩ)|kính\s+chào\s+bác\s+sĩ|"
    r"cảm\s+ơn\s+bạn\s+đã\s+(?:gửi\s+)?câu\s+hỏi)\b"
)
CONSULTATION_CLOSING_RE = re.compile(
    r"(?i)\b(?:chúc\s+bạn\s+(?:nhiều\s+)?sức\s+kh(?:ỏe|oẻ|oe)|"
    r"bạn\s+nên\s+(?:đến|đi)\s+(?:khám|gặp\s+bác\s+sĩ)|"
    r"theo\s+hướng\s+dẫn\s+của\s+bác\s+sĩ)\b"
)

CLINICAL_HEADING_PATTERNS = {
    "history": re.compile(
        r"(?i)\b(?:tiền\s+sử\s+bệnh(?!\s+hiện\s+tại)"
        r"(?:\s+(?:nội\s+khoa|lý|nội))?|lịch\s+sử\s+bệnh"
        r"(?!\s+hiện\s+tại))\b"
    ),
    "present_illness": re.compile(
        r"(?i)\b(?:tiền\s+sử\s+bệnh\s+hiện\s+tại|"
        r"bệnh\s+sử\s+hiện\s+tại|lịch\s+sử\s+bệnh\s+hiện\s+tại)\b"
    ),
    "hospital_assessment": re.compile(
        r"(?i)\bđánh\s+giá\s+tại\s+bệnh\s+viện\b"
    ),
}
CANONICAL_CLINICAL_HEADING_RE = re.compile(
    r"(?i)(?P<h1>1\.\s{0,3}(?:tiền\s+sử|lịch\s+sử))|"
    r"(?P<h2>2\.\s{0,3}(?:tiền\s+sử|bệnh\s+sử|lịch\s+sử))|"
    r"(?P<h3>3\.\s{0,3}(?:đánh\s+giá|khám|thăm\s+khám))"
)
CLINICAL_FIELD_RE = re.compile(
    r"(?i)\b(?:lý\s+do\s+nhập\s+viện|thời\s+điểm\s+khởi\s+phát|"
    r"thuốc\s+trước\s+khi\s+nhập\s+viện|các\s+bệnh\s+lý\s+m[aã]n\s+tính|"
    r"tiền\s+sử\s+phẫu\s+thuật|kết\s+quả\s+phòng\s+thí\s+nghiệm|"
    r"kết\s+quả\s+chẩn\s+đoán\s+hình\s+ảnh|thủ\s+thuật\s+(?:đã\s+)?"
    r"(?:được\s+)?thực\s+hiện|sự\s+kiện\s+trước\s+khi\s+nhập\s+viện)\b"
)
PATIENT_SPECIFIC_RE = re.compile(
    r"(?i)\b(?:bệnh\s+nhân|BN)\s+(?:nam|nữ|\d|\b)|"
    r"\b(?:ông|bà)\s+ấy\b|\bnhập\s+viện\b|\bvào\s+viện\b"
)
CASE_OPENING_RE = re.compile(
    r"(?i)^\s*(?:bệnh\s+nhân|BN)\s+(?:nam|nữ)?\s*\d{1,3}\s*tuổi"
)

EDUCATION_HEADING_RE = re.compile(
    r"(?i)\b(?:là\s+gì|là\s+bệnh\s+gì|nguyên\s+nhân|cơ\s+chế\s+bệnh\s+sinh|"
    r"dấu\s+hiệu|triệu\s+chứng|chẩn\s+đoán|điều\s+trị|phòng\s+ngừa|"
    r"biến\s+chứng|có\s+nguy\s+hiểm|chế\s+độ\s+dinh\s+dưỡng|"
    r"yếu\s+tố\s+nguy\s+cơ|theo\s+dõi|kết\s+luận)\b"
)
EDUCATION_PROSE_RE = re.compile(
    r"(?i)\b(?:cho\s+đến\s+nay|các\s+nhà\s+khoa\s+học|"
    r"nhiều\s+chuyên\s+gia|được\s+định\s+nghĩa\s+là|"
    r"tóm\s+lại|điều\s+quan\s+trọng|theo\s+khuyến\s+cáo|"
    r"người\s+bệnh\s+cần|cha\s+mẹ\s+cần|phụ\s+huynh\s+cần)\b"
)

REDACTION_RE = re.compile(r"\*{3,}")
PLACEHOLDER_RE = re.compile(r"\[[^\]\n]{2,60}\]")
MARKDOWN_RE = re.compile(
    r"(?<!\*)\*\*(?!\*)|^\s*\*\s+|^\s*#{1,6}\s+", re.MULTILINE
)
MOJIBAKE_RE = re.compile(r"(?:\ufffd|â€|Ã©|Ã¨|Ãª|Ä‘)")
LOWER_CHARS = (
    "a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩị"
    "òóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ"
)
UPPER_CHARS = (
    "A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊ"
    "ÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ"
)
LOWER_UPPER_GLUE_RE = re.compile(
    rf"(?<=[{LOWER_CHARS}])(?=[{UPPER_CHARS}])"
)
PUNCT_UPPER_GLUE_RE = re.compile(
    rf"(?<=[.!?])(?=[{UPPER_CHARS}])"
)
CONSECUTIVE_WORD_RE = re.compile(r"(?iu)\b([\wÀ-ỹ]{2,})\s+\1\b")
CONCAT_REPEAT_RE = re.compile(r"(?iu)([\wÀ-ỹ]{4,})\1")
LEGACY_PHRASE_REPEAT_RE = re.compile(r"(.{6,}?)\1")
HEADING_GLUE_RE = re.compile(
    rf"(?i)(?:tiền\s+sử\s+bệnh\s+hiện\s+tại|bệnh\s+sử\s+hiện\s+tại|"
    rf"đánh\s+giá\s+tại\s+bệnh\s+viện)(?=[{UPPER_CHARS}])"
)
MULTISPACE_RE = re.compile(r"[^\S\n]{2,}")
INLINE_ASCII_BULLET_RE = re.compile(
    r"(?<=\S)[^\S\n]{2,}[-*+][^\S\n]+"
)
ATTACHED_NUMBER_UNIT_RE = re.compile(
    r"(?i)(?<!\w)\d+(?:[.,]\d+)?(?:"
    r"micromol/l|mmol/l|µmol/l|ml/ngày|mg/dl|mmhg|mcg|l/ph|l/p|g/l|u/l|"
    r"mg|ml|cm|kg|fr|cc|g"
    r")(?!\w)"
)

CONTENT_STOPWORDS = {
    "ạ",
    "ai",
    "anh",
    "bác",
    "bạn",
    "bị",
    "bởi",
    "các",
    "cần",
    "cho",
    "chào",
    "chỉ",
    "có",
    "của",
    "cũng",
    "đã",
    "đang",
    "để",
    "đến",
    "được",
    "em",
    "gì",
    "hiện",
    "hỏi",
    "không",
    "khi",
    "là",
    "làm",
    "lại",
    "mà",
    "một",
    "mong",
    "mình",
    "này",
    "nên",
    "nếu",
    "người",
    "như",
    "những",
    "nhiều",
    "ở",
    "ra",
    "rất",
    "sau",
    "sẽ",
    "thì",
    "trong",
    "trên",
    "tôi",
    "từ",
    "và",
    "về",
    "với",
    "xin",
}

# Exact English/acronym signals are intentionally broad: this is a density
# measure, not a language identifier.
ASCII_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")


def natural_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.stem), path.name
    except ValueError:
        return 10**9, path.name


def normalize_space(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(unicodedata.normalize("NFC", text).lower())


def shingles(words: Sequence[str], n: int) -> set[tuple[str, ...]]:
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def quantiles(values: Sequence[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {"min": 0, "p25": 0, "median": 0, "p75": 0, "max": 0}

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        index = (len(ordered) - 1) * p
        low = int(index)
        high = min(low + 1, len(ordered) - 1)
        frac = index - low
        return ordered[low] * (1 - frac) + ordered[high] * frac

    return {
        "min": ordered[0],
        "p25": percentile(0.25),
        "median": percentile(0.5),
        "p75": percentile(0.75),
        "max": ordered[-1],
    }


def match_count(pattern: re.Pattern[str], text: str) -> int:
    return sum(1 for _ in pattern.finditer(text))


def detect_inline_bullets(lines: Sequence[str]) -> int:
    count = 0
    for line in lines:
        for match in UNICODE_BULLET_RE.finditer(line):
            if line[: match.start()].strip():
                count += 1
        count += match_count(INLINE_ASCII_BULLET_RE, line)
    return count


def canonical_heading_sequence(text: str) -> list[int]:
    sequence: list[int] = []
    for match in CANONICAL_CLINICAL_HEADING_RE.finditer(text):
        if match.lastgroup == "h1":
            sequence.append(1)
        elif match.lastgroup == "h2":
            sequence.append(2)
        elif match.lastgroup == "h3":
            sequence.append(3)
    return sequence


def qa_lexical_overlap(
    text: str,
) -> tuple[float | None, float | None, int, int]:
    """Return content-token Jaccard/overlap coefficient for the first Q/A pair.

    This is only a transparent mismatch proxy. It cannot replace semantic
    compatibility because Vietnamese paraphrases may share few surface tokens.
    """

    questions = list(QUESTION_LABEL_RE.finditer(text))
    answers = list(ANSWER_LABEL_RE.finditer(text))
    if not questions or not answers:
        return None, None, 0, 0

    question = questions[0]
    answer = next(
        (candidate for candidate in answers if candidate.start() > question.end()),
        None,
    )
    if answer is None:
        return None, None, 0, 0

    question_words = {
        word
        for word in tokens(text[question.end() : answer.start()])
        if len(word) >= 2 and word not in CONTENT_STOPWORDS
    }
    answer_words = {
        word
        for word in tokens(text[answer.end() :])
        if len(word) >= 2 and word not in CONTENT_STOPWORDS
    }
    if not question_words or not answer_words:
        return None, None, len(question_words), len(answer_words)

    intersection = len(question_words & answer_words)
    union = len(question_words | answer_words)
    minimum = min(len(question_words), len(answer_words))
    return (
        round(intersection / max(1, union), 4),
        round(intersection / max(1, minimum), 4),
        len(question_words),
        len(answer_words),
    )


def repeated_nonempty_lines(lines: Sequence[str]) -> tuple[int, int]:
    normalized = [
        normalize_space(line).casefold()
        for line in lines
        if len(normalize_space(line)) >= 30
    ]
    counts = Counter(normalized)
    types = sum(1 for count in counts.values() if count > 1)
    extras = sum(count - 1 for count in counts.values() if count > 1)
    return types, extras


def repeated_paragraphs(text: str) -> tuple[int, int]:
    paragraphs = [
        normalize_space(block).casefold()
        for block in re.split(r"\n\s*\n", text)
        if len(normalize_space(block)) >= 80
    ]
    counts = Counter(paragraphs)
    types = sum(1 for count in counts.values() if count > 1)
    extras = sum(count - 1 for count in counts.values() if count > 1)
    return types, extras


def numbered_headings(lines: Sequence[str]) -> list[tuple[int, str, int]]:
    found: list[tuple[int, str, int]] = []
    for line_number, line in enumerate(lines, start=1):
        match = SHORT_NUMBERED_HEADING_RE.match(line)
        if not match:
            continue
        title = normalize_space(match.group(2))
        # A very long prose sentence beginning with an ordinal is not treated
        # as a heading. The 140-char regex already removes most such cases.
        found.append((int(match.group(1)), title, line_number))
    return found


def duplicate_numbered_headings(
    headings: Sequence[tuple[int, str, int]]
) -> tuple[int, int]:
    normalized = [
        (number, normalize_space(title).casefold()) for number, title, _ in headings
    ]
    exact_counts = Counter(normalized)
    exact_extra = sum(count - 1 for count in exact_counts.values() if count > 1)
    adjacent_repeat = sum(
        1 for left, right in zip(normalized, normalized[1:]) if left == right
    )
    return exact_extra, adjacent_repeat


def starts_like_fragment(nonempty_lines: Sequence[str]) -> bool:
    if not nonempty_lines:
        return True
    first = nonempty_lines[0].strip()
    first_fold = first.casefold()
    if BULLET_LINE_RE.match(first):
        return True
    if first_fold.startswith(
        (
            "thêm.",
            "điều trị phụ thuộc",
            "có ý định điều trị",
            "cận lâm sàng",
            "các bệnh mãn tính",
            "các bệnh lý mãn tính",
            "câu trả lời của bác sĩ",
        )
    ):
        return True
    return False


def classify_document(text: str) -> dict[str, object]:
    lines = text.splitlines()
    nonempty = [line for line in lines if line.strip()]
    paragraph_list = [
        normalize_space(block)
        for block in re.split(r"\n\s*\n", text)
        if normalize_space(block)
    ]
    word_list = tokens(text)
    headings = numbered_headings(lines)
    canonical_sequence = canonical_heading_sequence(text)

    bullet_line_count = sum(bool(BULLET_LINE_RE.match(line)) for line in lines)
    dash_list_count = sum(
        bool(re.match(r"^\s*[-*+]\s+", line)) for line in lines
    )
    unicode_bullet_line_count = sum(
        bool(re.match(r"^\s*[•●▪◦‣]\s*", line)) for line in lines
    )
    numbered_line_start_count = sum(
        bool(re.match(r"^\s*\d{1,2}\s*[.)]\s*", line)) for line in lines
    )
    list_marker_count = (
        dash_list_count + unicode_bullet_line_count + numbered_line_start_count
    )
    inline_bullet_count = detect_inline_bullets(lines)
    heading_inline_bullet_count = sum(
        1
        for line in lines
        if NUMBERED_LINE_RE.match(line) and UNICODE_BULLET_RE.search(line)
    )

    clinical_heading_hits = {
        key: match_count(pattern, text)
        for key, pattern in CLINICAL_HEADING_PATTERNS.items()
    }
    clinical_sections = sum(value > 0 for value in clinical_heading_hits.values())
    clinical_heading_total = sum(clinical_heading_hits.values())
    clinical_field_hits = match_count(CLINICAL_FIELD_RE, text)
    patient_specific_hits = match_count(PATIENT_SPECIFIC_RE, text)
    case_opening = bool(nonempty and CASE_OPENING_RE.search(nonempty[0]))

    education_heading_count = sum(
        bool(EDUCATION_HEADING_RE.search(title)) for _, title, _ in headings
    )
    education_prose_hits = match_count(EDUCATION_PROSE_RE, text)
    definition_title = any(
        re.search(r"(?i)\b(?:là\s+gì|là\s+bệnh\s+gì)\s*\??$", title)
        for _, title, _ in headings
    ) or bool(
        nonempty
        and re.search(r"(?i)\b(?:là\s+gì|là\s+bệnh\s+gì)\s*\??$", nonempty[0])
    )

    question_label_hits = match_count(QUESTION_LABEL_RE, text)
    answer_label_hits = match_count(ANSWER_LABEL_RE, text)
    greeting_hits = match_count(DOCTOR_GREETING_RE, text)
    consultation_closing_hits = match_count(CONSULTATION_CLOSING_RE, text)
    qa_complete = question_label_hits > 0 and answer_label_hits > 0
    qa_partial = (question_label_hits > 0) != (answer_label_hits > 0)
    qa_implicit = (
        question_label_hits + answer_label_hits == 0
        and greeting_hits > 0
        and consultation_closing_hits > 0
    )
    (
        qa_token_jaccard,
        qa_token_overlap_coefficient,
        qa_question_content_tokens,
        qa_answer_content_tokens,
    ) = qa_lexical_overlap(text)

    # These are intentionally precision-oriented genre flags. A weak mention of
    # "bệnh nhân" inside a general article does not by itself create a genre.
    genre_qa = qa_complete or (
        question_label_hits + answer_label_hits > 0 and greeting_hits > 0
    ) or qa_implicit
    genre_clinical = (
        clinical_sections >= 2
        or clinical_field_hits >= 3
        or case_opening
        or (patient_specific_hits >= 3 and clinical_field_hits >= 1)
    )
    genre_education = (
        education_heading_count >= 2
        or definition_title
        or (education_heading_count >= 1 and education_prose_hits >= 2)
    )
    genre_count = sum((genre_qa, genre_clinical, genre_education))

    line_lengths = [len(line) for line in nonempty]
    max_line_chars = max(line_lengths, default=0)
    longest_line_share = max_line_chars / max(1, len(text))
    compacted = (
        longest_line_share >= 0.72
        or (len(nonempty) <= 3 and max_line_chars >= 500)
    )
    fragment_start = starts_like_fragment(nonempty)

    if genre_qa and not compacted:
        layout_proxy = "qa_dialogue"
    elif genre_education and len(headings) >= 2 and not compacted:
        layout_proxy = "numbered_health_article"
    elif genre_clinical and clinical_sections >= 2 and not compacted:
        layout_proxy = "numbered_clinical_template"
    elif case_opening and not compacted:
        layout_proxy = "narrative_case"
    elif compacted or (len(nonempty) <= 5 and fragment_start):
        layout_proxy = "fragment_or_compacted"
    else:
        layout_proxy = "freeform_or_hybrid"

    duplicate_heading_extra, adjacent_duplicate_heading = (
        duplicate_numbered_headings(headings)
    )
    repeated_canonical_heading_extra = sum(
        max(0, count - 1) for count in Counter(canonical_sequence).values()
    )
    repeated_line_types, repeated_line_extra = repeated_nonempty_lines(lines)
    repeated_para_types, repeated_para_extra = repeated_paragraphs(text)

    redaction_runs = match_count(REDACTION_RE, text)
    redaction_chars = sum(len(match.group()) for match in REDACTION_RE.finditer(text))
    placeholders = match_count(PLACEHOLDER_RE, text)
    lower_upper_glue = match_count(LOWER_UPPER_GLUE_RE, text)
    punct_upper_glue = match_count(PUNCT_UPPER_GLUE_RE, text)
    heading_glue = match_count(HEADING_GLUE_RE, text)
    consecutive_word_repeats = match_count(CONSECUTIVE_WORD_RE, text)
    concatenated_repeats = match_count(CONCAT_REPEAT_RE, text)
    legacy_phrase_repeats = match_count(LEGACY_PHRASE_REPEAT_RE, text)
    attached_number_units = match_count(ATTACHED_NUMBER_UNIT_RE, text)
    multiple_space_runs = match_count(MULTISPACE_RE, text)
    markdown_hits = match_count(MARKDOWN_RE, text)
    mojibake_hits = match_count(MOJIBAKE_RE, text)
    decomposed_codepoints = sum(
        1 for char in text if unicodedata.combining(char) and char.strip()
    )

    embedded_qa = genre_qa and genre_clinical
    embedded_article_clinical = genre_education and genre_clinical
    clinical_field_intrusion = (
        genre_qa and not genre_clinical and clinical_field_hits > 0
    )
    clinical_heading_intrusion = (
        clinical_heading_total > 0
        and clinical_sections < 2
        and (genre_qa or genre_education)
    )
    abnormal_label_position = False
    for pattern in (QUESTION_LABEL_RE, ANSWER_LABEL_RE):
        matches = list(pattern.finditer(text))
        if matches and min(match.start() for match in matches) > len(text) * 0.35:
            abnormal_label_position = True

    # High-precision signals only; a value of zero does not mean "clean".
    stitching_signals = sum(
        (
            genre_count >= 2,
            clinical_heading_intrusion,
            clinical_field_intrusion,
            duplicate_heading_extra > 0,
            repeated_canonical_heading_extra > 0,
            heading_glue > 0,
            heading_inline_bullet_count > 0,
            fragment_start and genre_count >= 1,
        )
    )

    alpha_words = [word for word in TOKEN_RE.findall(text) if word.isalpha()]
    ascii_words = ASCII_WORD_RE.findall(text)

    return {
        "chars": len(text),
        "tokens": len(word_list),
        "physical_lines": len(lines),
        "nonempty_lines": len(nonempty),
        "paragraphs": len(paragraph_list),
        "max_line_chars": max_line_chars,
        "longest_line_share": round(longest_line_share, 4),
        "lines_ge_300_chars": sum(length >= 300 for length in line_lengths),
        "lines_ge_500_chars": sum(length >= 500 for length in line_lengths),
        "lines_ge_600_chars": sum(length >= 600 for length in line_lengths),
        "lines_ge_1000_chars": sum(length >= 1000 for length in line_lengths),
        "mean_chars_per_nonempty_line": round(
            len(text) / max(1, len(nonempty)), 2
        ),
        "bullet_line_count": bullet_line_count,
        "bullet_line_ratio": round(bullet_line_count / max(1, len(nonempty)), 4),
        "dash_list_count": dash_list_count,
        "unicode_bullet_line_count": unicode_bullet_line_count,
        "numbered_line_start_count": numbered_line_start_count,
        "list_marker_count": list_marker_count,
        "inline_bullet_count": inline_bullet_count,
        "heading_inline_bullet_count": heading_inline_bullet_count,
        "numbered_heading_count": len(headings),
        "heading_numbers": ",".join(str(number) for number, _, _ in headings),
        "duplicate_numbered_heading_extra": duplicate_heading_extra,
        "adjacent_duplicate_heading_count": adjacent_duplicate_heading,
        "canonical_clinical_sequence": ",".join(
            str(number) for number in canonical_sequence
        ),
        "canonical_heading_count": len(canonical_sequence),
        "canonical_full_1_2_3": canonical_sequence == [1, 2, 3],
        "canonical_partial_or_malformed": bool(canonical_sequence)
        and canonical_sequence != [1, 2, 3],
        "clinical_section_count": clinical_sections,
        "clinical_heading_total": clinical_heading_total,
        "clinical_history_hits": clinical_heading_hits["history"],
        "clinical_present_illness_hits": clinical_heading_hits["present_illness"],
        "clinical_assessment_hits": clinical_heading_hits["hospital_assessment"],
        "clinical_field_hits": clinical_field_hits,
        "patient_specific_hits": patient_specific_hits,
        "case_opening": case_opening,
        "education_heading_count": education_heading_count,
        "education_prose_hits": education_prose_hits,
        "definition_title": definition_title,
        "question_label_hits": question_label_hits,
        "answer_label_hits": answer_label_hits,
        "doctor_greeting_hits": greeting_hits,
        "consultation_closing_hits": consultation_closing_hits,
        "qa_complete": qa_complete,
        "qa_partial": qa_partial,
        "qa_implicit_without_marker": qa_implicit,
        "qa_content_token_jaccard": (
            "" if qa_token_jaccard is None else qa_token_jaccard
        ),
        "qa_content_token_overlap_coefficient": (
            ""
            if qa_token_overlap_coefficient is None
            else qa_token_overlap_coefficient
        ),
        "qa_question_content_tokens": qa_question_content_tokens,
        "qa_answer_content_tokens": qa_answer_content_tokens,
        "genre_qa": genre_qa,
        "genre_clinical": genre_clinical,
        "genre_health_education": genre_education,
        "major_genre_count": genre_count,
        "mixed_major_genre": genre_count >= 2,
        "layout_proxy": layout_proxy,
        "compacted_layout": compacted,
        "fragment_start": fragment_start,
        "embedded_qa_clinical": embedded_qa,
        "embedded_article_clinical": embedded_article_clinical,
        "clinical_field_intrusion": clinical_field_intrusion,
        "clinical_heading_intrusion": clinical_heading_intrusion,
        "abnormal_qa_label_position": abnormal_label_position,
        "stitching_signal_count": stitching_signals,
        "redaction_runs": redaction_runs,
        "redaction_chars": redaction_chars,
        "placeholder_hits": placeholders,
        "markdown_hits": markdown_hits,
        "mojibake_hits": mojibake_hits,
        "decomposed_codepoints": decomposed_codepoints,
        "lower_upper_glue_hits": lower_upper_glue,
        "punct_upper_glue_hits": punct_upper_glue,
        "heading_glue_hits": heading_glue,
        "repeated_canonical_heading_extra": repeated_canonical_heading_extra,
        "consecutive_word_repeat_hits": consecutive_word_repeats,
        "concatenated_repeat_hits": concatenated_repeats,
        "legacy_phrase_repeat_hits": legacy_phrase_repeats,
        "legacy_glue_or_repeat_proxy": (
            lower_upper_glue + legacy_phrase_repeats
        )
        > 0,
        "attached_number_unit_hits": attached_number_units,
        "multiple_space_runs": multiple_space_runs,
        "leading_indent_lines": sum(
            bool(re.match(r"^[ \t]+\S", line)) for line in lines
        ),
        "trailing_space_lines": sum(
            bool(re.search(r"[ \t]+$", line)) for line in lines
        ),
        "tab_count": text.count("\t"),
        "zero_width_space_count": text.count("\u200b"),
        "nbsp_count": text.count("\u00a0"),
        "carriage_return_count": text.count("\r"),
        "has_utf8_bom": text.startswith("\ufeff"),
        "repeated_line_types": repeated_line_types,
        "repeated_line_extra": repeated_line_extra,
        "repeated_paragraph_types": repeated_para_types,
        "repeated_paragraph_extra": repeated_para_extra,
        "ascii_word_count": len(ascii_words),
        "ascii_word_ratio": round(len(ascii_words) / max(1, len(alpha_words)), 4),
    }


def build_cross_document_reuse(
    texts: dict[str, str],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    word_lists = {name: tokens(text) for name, text in texts.items()}
    grams7 = {name: shingles(words, 7) for name, words in word_lists.items()}
    grams8 = {name: shingles(words, 8) for name, words in word_lists.items()}
    grams12 = {name: shingles(words, 12) for name, words in word_lists.items()}

    doc_frequency7: Counter[tuple[str, ...]] = Counter()
    for grams in grams7.values():
        doc_frequency7.update(grams)
    doc_frequency: Counter[tuple[str, ...]] = Counter()
    for grams in grams12.values():
        doc_frequency.update(grams)

    per_file: dict[str, dict[str, object]] = {}
    for name, grams in grams12.items():
        reused = {gram for gram in grams if doc_frequency[gram] >= 2}
        reused7 = {
            gram for gram in grams7[name] if doc_frequency7[gram] >= 2
        }
        per_file[name] = {
            "reused_7gram_count": len(reused7),
            "reused_7gram_ratio": round(
                len(reused7) / max(1, len(grams7[name])), 4
            ),
            "reused_12gram_count": len(reused),
            "reused_12gram_ratio": round(len(reused) / max(1, len(grams)), 4),
            "strong_reuse_neighbor_count": 0,
            "nearest_reuse_file": "",
            "nearest_reuse_containment": 0.0,
            "nearest_reuse_jaccard": 0.0,
            "nearest_shared_8grams": 0,
        }

    pairs: list[dict[str, object]] = []
    names = sorted(texts, key=lambda value: int(Path(value).stem))
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            intersection = grams8[left] & grams8[right]
            shared = len(intersection)
            if shared == 0:
                continue
            minimum = min(len(grams8[left]), len(grams8[right]))
            union = len(grams8[left] | grams8[right])
            containment = shared / max(1, minimum)
            jaccard = shared / max(1, union)

            for source, other in ((left, right), (right, left)):
                state = per_file[source]
                current = float(state["nearest_reuse_containment"])
                if containment > current:
                    state["nearest_reuse_file"] = other
                    state["nearest_reuse_containment"] = round(containment, 4)
                    state["nearest_reuse_jaccard"] = round(jaccard, 4)
                    state["nearest_shared_8grams"] = shared
                if containment >= 0.30 and shared >= 40:
                    state["strong_reuse_neighbor_count"] = (
                        int(state["strong_reuse_neighbor_count"]) + 1
                    )

            # Store only material pairs. This keeps the CSV auditable while
            # avoiding thousands of weak overlaps from common medical phrases.
            if shared < 40 or containment < 0.12:
                continue

            matcher = SequenceMatcher(
                None, word_lists[left], word_lists[right], autojunk=False
            )
            longest = matcher.find_longest_match(
                0,
                len(word_lists[left]),
                0,
                len(word_lists[right]),
            )
            excerpt = " ".join(
                word_lists[left][longest.a : longest.a + min(longest.size, 28)]
            )
            pairs.append(
                {
                    "file_a": left,
                    "file_b": right,
                    "shared_8grams": shared,
                    "containment_smaller": round(containment, 4),
                    "jaccard": round(jaccard, 4),
                    "longest_exact_token_run": longest.size,
                    "shared_excerpt": excerpt,
                }
            )

    pairs.sort(
        key=lambda row: (
            -float(row["containment_smaller"]),
            -int(row["shared_8grams"]),
            str(row["file_a"]),
            str(row["file_b"]),
        )
    )
    return pairs, per_file


def build_repeated_line_table(
    texts: dict[str, str],
) -> list[dict[str, object]]:
    occurrences: defaultdict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for name, text in texts.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            clean = normalize_space(line)
            if len(clean) < 45:
                continue
            normalized = unicodedata.normalize("NFC", clean).casefold()
            occurrences[normalized].append((name, line_number, clean))

    rows: list[dict[str, object]] = []
    for found in occurrences.values():
        documents = sorted(
            {name for name, _, _ in found},
            key=lambda value: int(Path(value).stem),
        )
        if len(documents) < 2:
            continue
        example = found[0][2]
        rows.append(
            {
                "document_count": len(documents),
                "occurrence_count": len(found),
                "files": ",".join(documents),
                "chars": len(example),
                "text": example,
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["document_count"]),
            -int(row["chars"]),
            str(row["text"]),
        )
    )
    return rows


def connected_components(
    names: Iterable[str],
    pairs: Sequence[dict[str, object]],
    containment_threshold: float,
) -> list[list[str]]:
    graph: defaultdict[str, set[str]] = defaultdict(set)
    for row in pairs:
        if float(row["containment_smaller"]) < containment_threshold:
            continue
        left = str(row["file_a"])
        right = str(row["file_b"])
        graph[left].add(right)
        graph[right].add(left)

    seen: set[str] = set()
    components: list[list[str]] = []
    for name in names:
        if name in seen or not graph[name]:
            continue
        stack = [name]
        component: list[str] = []
        seen.add(name)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        component.sort(key=lambda value: int(Path(value).stem))
        components.append(component)
    components.sort(key=lambda group: (-len(group), int(Path(group[0]).stem)))
    return components


def count_true(
    rows: Sequence[dict[str, object]], key: str, predicate=bool
) -> int:
    return sum(bool(predicate(row[key])) for row in rows)


def files_where(
    rows: Sequence[dict[str, object]], key: str, predicate=bool
) -> list[str]:
    return [str(row["file"]) for row in rows if predicate(row[key])]


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    files = sorted(INPUT_DIR.glob("*.txt"), key=natural_key)
    if not files:
        raise FileNotFoundError(f"No .txt files found under {INPUT_DIR}")

    texts = {path.name: path.read_text(encoding="utf-8") for path in files}
    reuse_pairs, reuse_features = build_cross_document_reuse(texts)

    rows: list[dict[str, object]] = []
    for path in files:
        row = {"file": path.name, **classify_document(texts[path.name])}
        row.update(reuse_features[path.name])
        rows.append(row)

    repeated_lines = build_repeated_line_table(texts)
    repeated_line_counts: Counter[str] = Counter()
    for repeated in repeated_lines:
        for name in str(repeated["files"]).split(","):
            repeated_line_counts[name] += 1
    for row in rows:
        row["cross_document_repeated_line_count"] = repeated_line_counts[
            str(row["file"])
        ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "turn2_structure_features.csv", rows)
    write_csv(OUTPUT_DIR / "turn2_reuse_pairs.csv", reuse_pairs)
    write_csv(OUTPUT_DIR / "turn2_repeated_lines.csv", repeated_lines)

    layouts = Counter(str(row["layout_proxy"]) for row in rows)
    genre_combinations = Counter(
        "+".join(
            name
            for name, key in (
                ("qa", "genre_qa"),
                ("clinical", "genre_clinical"),
                ("education", "genre_health_education"),
            )
            if row[key]
        )
        or "unclassified"
        for row in rows
    )
    components_45 = connected_components(texts, reuse_pairs, 0.45)
    components_50 = connected_components(texts, reuse_pairs, 0.50)
    components_75 = connected_components(texts, reuse_pairs, 0.75)
    redaction_lengths = [
        len(match.group())
        for text in texts.values()
        for match in REDACTION_RE.finditer(text)
    ]
    placeholder_types = Counter(
        match.group()
        for text in texts.values()
        for match in PLACEHOLDER_RE.finditer(text)
    )

    summary = {
        "input_dir": str(INPUT_DIR.relative_to(ROOT)),
        "document_count": len(rows),
        "corpus_totals": {
            "chars": sum(int(row["chars"]) for row in rows),
            "tokens": sum(int(row["tokens"]) for row in rows),
            "physical_lines": sum(int(row["physical_lines"]) for row in rows),
            "nonempty_lines": sum(int(row["nonempty_lines"]) for row in rows),
        },
        "length": {
            "chars": quantiles([int(row["chars"]) for row in rows]),
            "tokens": quantiles([int(row["tokens"]) for row in rows]),
            "physical_lines": quantiles(
                [int(row["physical_lines"]) for row in rows]
            ),
            "nonempty_lines": quantiles(
                [int(row["nonempty_lines"]) for row in rows]
            ),
            "paragraphs": quantiles([int(row["paragraphs"]) for row in rows]),
            "max_line_chars": quantiles(
                [int(row["max_line_chars"]) for row in rows]
            ),
        },
        "layout_proxy_counts": dict(sorted(layouts.items())),
        "genre_combination_counts": dict(
            sorted(genre_combinations.items(), key=lambda item: (-item[1], item[0]))
        ),
        "genre_counts_multilabel": {
            "qa": count_true(rows, "genre_qa"),
            "clinical": count_true(rows, "genre_clinical"),
            "health_education": count_true(rows, "genre_health_education"),
            "mixed_major_genre": count_true(rows, "mixed_major_genre"),
        },
        "structure_counts": {
            "has_any_numbered_heading": count_true(
                rows, "numbered_heading_count", lambda value: int(value) > 0
            ),
            "has_any_canonical_clinical_heading": count_true(
                rows, "canonical_heading_count", lambda value: int(value) > 0
            ),
            "canonical_full_exact_1_2_3": count_true(
                rows, "canonical_full_1_2_3"
            ),
            "canonical_partial_or_malformed": count_true(
                rows, "canonical_partial_or_malformed"
            ),
            "canonical_sequence_counts": dict(
                sorted(
                    Counter(
                        str(row["canonical_clinical_sequence"]) or "none"
                        for row in rows
                    ).items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ),
            "has_all_3_clinical_sections": count_true(
                rows, "clinical_section_count", lambda value: int(value) == 3
            ),
            "complete_qa_labels": count_true(rows, "qa_complete"),
            "partial_qa_labels": count_true(rows, "qa_partial"),
            "qa_marker_any": count_true(
                rows,
                "question_label_hits",
                lambda value: int(value) > 0,
            )
            + count_true(
                rows,
                "answer_label_hits",
                lambda value: int(value) > 0,
            )
            - count_true(rows, "qa_complete"),
            "qa_question_only": sum(
                int(row["question_label_hits"]) > 0
                and int(row["answer_label_hits"]) == 0
                for row in rows
            ),
            "qa_answer_only": sum(
                int(row["answer_label_hits"]) > 0
                and int(row["question_label_hits"]) == 0
                for row in rows
            ),
            "compacted_layout": count_true(rows, "compacted_layout"),
            "fragment_start": count_true(rows, "fragment_start"),
            "list_marker_count_quantiles": quantiles(
                [int(row["list_marker_count"]) for row in rows]
            ),
            "has_dash_list": count_true(
                rows, "dash_list_count", lambda value: int(value) > 0
            ),
            "has_unicode_bullet_list": count_true(
                rows,
                "unicode_bullet_line_count",
                lambda value: int(value) > 0,
            ),
            "has_numbered_line_start": count_true(
                rows,
                "numbered_line_start_count",
                lambda value: int(value) > 0,
            ),
            "has_bullet_line": count_true(
                rows, "bullet_line_count", lambda value: int(value) > 0
            ),
            "has_inline_bullet": count_true(
                rows, "inline_bullet_count", lambda value: int(value) > 0
            ),
            "has_heading_inline_bullet": count_true(
                rows, "heading_inline_bullet_count", lambda value: int(value) > 0
            ),
            "has_duplicate_numbered_heading": count_true(
                rows,
                "duplicate_numbered_heading_extra",
                lambda value: int(value) > 0,
            ),
            "has_repeated_canonical_heading": count_true(
                rows,
                "repeated_canonical_heading_extra",
                lambda value: int(value) > 0,
            ),
            "qa_marker_and_canonical_heading": sum(
                (
                    int(row["question_label_hits"]) > 0
                    or int(row["answer_label_hits"]) > 0
                )
                and int(row["canonical_heading_count"]) > 0
                for row in rows
            ),
            "list_density_buckets": {
                "0": sum(int(row["list_marker_count"]) == 0 for row in rows),
                "1_to_4": sum(
                    1 <= int(row["list_marker_count"]) <= 4 for row in rows
                ),
                "5_to_9": sum(
                    5 <= int(row["list_marker_count"]) <= 9 for row in rows
                ),
                "10_to_19": sum(
                    10 <= int(row["list_marker_count"]) <= 19 for row in rows
                ),
                "20_plus": sum(
                    int(row["list_marker_count"]) >= 20 for row in rows
                ),
            },
        },
        "noise_counts": {
            "redaction": count_true(
                rows, "redaction_runs", lambda value: int(value) > 0
            ),
            "redaction_run_total": sum(
                int(row["redaction_runs"]) for row in rows
            ),
            "redaction_run_length_min": min(redaction_lengths, default=0),
            "redaction_run_length_max": max(redaction_lengths, default=0),
            "placeholder": count_true(
                rows, "placeholder_hits", lambda value: int(value) > 0
            ),
            "placeholder_total": sum(
                int(row["placeholder_hits"]) for row in rows
            ),
            "placeholder_types": dict(
                sorted(
                    placeholder_types.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ),
            "lower_upper_glue": count_true(
                rows, "lower_upper_glue_hits", lambda value: int(value) > 0
            ),
            "punctuation_upper_glue": count_true(
                rows, "punct_upper_glue_hits", lambda value: int(value) > 0
            ),
            "punctuation_upper_glue_total": sum(
                int(row["punct_upper_glue_hits"]) for row in rows
            ),
            "heading_glue": count_true(
                rows, "heading_glue_hits", lambda value: int(value) > 0
            ),
            "legacy_glue_or_repeat_proxy": count_true(
                rows, "legacy_glue_or_repeat_proxy"
            ),
            "word_or_phrase_repeat": sum(
                int(row["consecutive_word_repeat_hits"]) > 0
                or int(row["concatenated_repeat_hits"]) > 0
                or int(row["repeated_line_extra"]) > 0
                or int(row["repeated_paragraph_extra"]) > 0
                for row in rows
            ),
            "internal_repeated_line_file_count": count_true(
                rows, "repeated_line_types", lambda value: int(value) > 0
            ),
            "internal_repeated_line_type_total": sum(
                int(row["repeated_line_types"]) for row in rows
            ),
            "internal_repeated_line_extra_total": sum(
                int(row["repeated_line_extra"]) for row in rows
            ),
            "attached_number_unit_file_count": count_true(
                rows, "attached_number_unit_hits", lambda value: int(value) > 0
            ),
            "attached_number_unit_total": sum(
                int(row["attached_number_unit_hits"]) for row in rows
            ),
            "decomposed_unicode": count_true(
                rows, "decomposed_codepoints", lambda value: int(value) > 0
            ),
            "mojibake": count_true(
                rows, "mojibake_hits", lambda value: int(value) > 0
            ),
            "markdown_syntax": count_true(
                rows, "markdown_hits", lambda value: int(value) > 0
            ),
            "leading_indent": count_true(
                rows, "leading_indent_lines", lambda value: int(value) > 0
            ),
            "leading_indent_line_total": sum(
                int(row["leading_indent_lines"]) for row in rows
            ),
            "trailing_space": count_true(
                rows, "trailing_space_lines", lambda value: int(value) > 0
            ),
            "trailing_space_line_total": sum(
                int(row["trailing_space_lines"]) for row in rows
            ),
            "tab": count_true(
                rows, "tab_count", lambda value: int(value) > 0
            ),
            "zero_width_space": count_true(
                rows, "zero_width_space_count", lambda value: int(value) > 0
            ),
            "nbsp": count_true(
                rows, "nbsp_count", lambda value: int(value) > 0
            ),
            "carriage_return": count_true(
                rows,
                "carriage_return_count",
                lambda value: int(value) > 0,
            ),
            "utf8_bom": count_true(rows, "has_utf8_bom"),
            "one_or_more_600_char_lines": count_true(
                rows, "lines_ge_600_chars", lambda value: int(value) > 0
            ),
            "one_or_more_300_char_lines": count_true(
                rows, "lines_ge_300_chars", lambda value: int(value) > 0
            ),
            "one_or_more_500_char_lines": count_true(
                rows, "lines_ge_500_chars", lambda value: int(value) > 0
            ),
            "one_or_more_1000_char_lines": count_true(
                rows, "lines_ge_1000_chars", lambda value: int(value) > 0
            ),
        },
        "stitching_counts": {
            "mixed_major_genre": count_true(rows, "mixed_major_genre"),
            "clinical_heading_intrusion": count_true(
                rows, "clinical_heading_intrusion"
            ),
            "clinical_field_intrusion": count_true(
                rows, "clinical_field_intrusion"
            ),
            "abnormal_qa_label_position": count_true(
                rows, "abnormal_qa_label_position"
            ),
            "at_least_1_high_precision_signal": count_true(
                rows, "stitching_signal_count", lambda value: int(value) >= 1
            ),
            "at_least_2_high_precision_signals": count_true(
                rows, "stitching_signal_count", lambda value: int(value) >= 2
            ),
        },
        "cross_document_reuse": {
            "material_pair_count": len(reuse_pairs),
            "files_with_any_reused_12gram": count_true(
                rows, "reused_12gram_count", lambda value: int(value) > 0
            ),
            "files_with_any_reused_7gram": count_true(
                rows, "reused_7gram_count", lambda value: int(value) > 0
            ),
            "files_with_any_exact_repeated_line_ge_45_chars": count_true(
                rows,
                "cross_document_repeated_line_count",
                lambda value: int(value) > 0,
            ),
            "files_with_2_exact_repeated_lines_ge_45_chars": count_true(
                rows,
                "cross_document_repeated_line_count",
                lambda value: int(value) >= 2,
            ),
            "files_with_5_exact_repeated_lines_ge_45_chars": count_true(
                rows,
                "cross_document_repeated_line_count",
                lambda value: int(value) >= 5,
            ),
            "files_reused_7gram_ratio_ge_0_50": count_true(
                rows, "reused_7gram_ratio", lambda value: float(value) >= 0.50
            ),
            "files_reused_7gram_ratio_ge_0_75": count_true(
                rows, "reused_7gram_ratio", lambda value: float(value) >= 0.75
            ),
            "files_reused_7gram_ratio_ge_0_90": count_true(
                rows, "reused_7gram_ratio", lambda value: float(value) >= 0.90
            ),
            "files_reused_12gram_ratio_ge_0_25": count_true(
                rows, "reused_12gram_ratio", lambda value: float(value) >= 0.25
            ),
            "files_nearest_containment_ge_0_30": count_true(
                rows,
                "nearest_reuse_containment",
                lambda value: float(value) >= 0.30,
            ),
            "files_nearest_containment_ge_0_50": count_true(
                rows,
                "nearest_reuse_containment",
                lambda value: float(value) >= 0.50,
            ),
            "files_nearest_containment_ge_0_75": count_true(
                rows,
                "nearest_reuse_containment",
                lambda value: float(value) >= 0.75,
            ),
            "reused_12gram_ratio": quantiles(
                [float(row["reused_12gram_ratio"]) for row in rows]
            ),
            "reused_7gram_ratio": {
                **quantiles(
                    [float(row["reused_7gram_ratio"]) for row in rows]
                ),
                "mean": statistics.fmean(
                    float(row["reused_7gram_ratio"]) for row in rows
                ),
            },
            "components_at_containment_0_45": components_45,
            "components_at_containment_0_50": components_50,
            "components_at_containment_0_75": components_75,
        },
        "selected_file_lists": {
            "mixed_major_genre": files_where(rows, "mixed_major_genre"),
            "compacted_layout": files_where(rows, "compacted_layout"),
            "fragment_start": files_where(rows, "fragment_start"),
            "redaction": files_where(
                rows, "redaction_runs", lambda value: int(value) > 0
            ),
            "heading_glue": files_where(
                rows, "heading_glue_hits", lambda value: int(value) > 0
            ),
            "stitching_signal_ge_2": files_where(
                rows, "stitching_signal_count", lambda value: int(value) >= 2
            ),
            "nearest_containment_ge_0_75": files_where(
                rows,
                "nearest_reuse_containment",
                lambda value: float(value) >= 0.75,
            ),
        },
        "method_notes": [
            "All categories are heuristic, multi-axis EDA features, not gold labels.",
            "No file ID is used to classify a document.",
            "Cross-document reuse uses exact NFC-normalized token 7/8/12-grams.",
            "Pair containment is intersection divided by the smaller shingle set.",
            "Repeated-line statistics use exact NFC/case/space-normalized lines of at least 45 characters.",
            "Counts from public competition input must not be used as training templates.",
        ],
    }

    summary_path = OUTPUT_DIR / "turn2_structure_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"documents={len(rows)}")
    print("layouts=" + json.dumps(dict(layouts), ensure_ascii=True, sort_keys=True))
    print(
        "genres="
        + json.dumps(
            summary["genre_counts_multilabel"], ensure_ascii=True, sort_keys=True
        )
    )
    print(
        "mixed_major_genre="
        + str(summary["genre_counts_multilabel"]["mixed_major_genre"])
    )
    print(
        "nearest_containment_ge_0.75="
        + str(
            summary["cross_document_reuse"][
                "files_nearest_containment_ge_0_75"
            ]
        )
    )
    print(f"wrote={OUTPUT_DIR / 'turn2_structure_features.csv'}")
    print(f"wrote={OUTPUT_DIR / 'turn2_reuse_pairs.csv'}")
    print(f"wrote={OUTPUT_DIR / 'turn2_repeated_lines.csv'}")
    print(f"wrote={summary_path}")


if __name__ == "__main__":
    main()
