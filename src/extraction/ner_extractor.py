# -*- coding: utf-8 -*-
"""NER inference (Tier 1): model token-classification -> Mention (span+type), offset trên raw.

- Sliding window (overflowing tokens) cho văn bản dài > maxlen.
- Gắn section_top (history/present/hospital) cho mỗi mention để rule assertion vẫn xài được
  (tái dùng bộ dò header của rule extractor, nhưng KHÔNG dùng nó để bắt khái niệm).
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import re

from .extractor import Mention, _iter_lines, _match_header, _LABEL
from ..common.text_norm import normalize_for_match
from ..schema import TYPE_CHAN_DOAN, TYPE_KQ_XN, TYPE_THUOC
from .ner_common import ID2LABEL, token_labels_to_char_spans

_ROOT = Path(__file__).resolve().parent.parent.parent

# stopword/từ nối hay bị NER bắt nhầm thành khái niệm
_STOPSPANS = {
    "và", "hoặc", "nhưng", "là", "của", "các", "có", "được", "cho", "với", "khi",
    "một", "khoảng một", "trong", "sau", "trước", "đã", "bị", "vào", "ra", "tại",
}


_WORDCH = re.compile(r"[0-9A-Za-zÀ-ỹ]")
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s*")


def _split_newlines(raw: str, s: int, e: int):
    """Tách span vượt xuống dòng thành nhiều span (mỗi dòng 1 khái niệm, bỏ bullet đầu).
    NER đôi khi gộp 2 bullet liền kề -> 1 span; tách lại theo \\n."""
    out = []
    seg_start = s
    text = raw[s:e]
    for part in text.split("\n"):
        ss = seg_start
        ee = seg_start + len(part)
        # bỏ bullet/khoảng trắng đầu đoạn
        m = _BULLET_PREFIX.match(raw[ss:ee])
        if m:
            ss += m.end()
        while ss < ee and raw[ss].isspace():
            ss += 1
        while ee > ss and raw[ee - 1].isspace():
            ee -= 1
        if ee > ss:
            out.append((ss, ee))
        seg_start += len(part) + 1  # +1 cho ký tự \n
    return out


def _snap_word(raw: str, s: int, e: int):
    """Co biên span để không cắt giữa từ (tránh 'Ng' từ 'Ngừng'); rồi strip khoảng trắng.

    Mở rộng thêm qua DẤU THẬP PHÂN (`.`/`,` giữa 2 chữ số) — bug đo được: model trúng '2' trong
    '5.2' -> bản cũ cắt còn '2', mất '5.'. KHÔNG thêm '.'/',' vào `_WORDCH` chung (sẽ phá ranh giới
    câu ở mọi chỗ khác dùng nó) — chỉ khớp đúng pattern hẹp digit-sep-digit. Xem
    docs/ANNOTATION_GUIDELINE.md §6 + docs/EXPERIMENTS_LOG.md (nhóm lỗi "cắt giữa số").
    """
    while s > 0:
        if _WORDCH.match(raw[s - 1] or "") and _WORDCH.match(raw[s] or ""):
            s -= 1
        elif s >= 2 and raw[s - 1] in ".," and raw[s - 2].isdigit() and raw[s].isdigit():
            s -= 2
        else:
            break
    while e < len(raw):
        if _WORDCH.match(raw[e - 1] or "") and _WORDCH.match(raw[e] or ""):
            e += 1
        elif e + 1 < len(raw) and raw[e] in ".," and raw[e - 1].isdigit() and raw[e + 1].isdigit():
            e += 2
        else:
            break
    while s < e and raw[s].isspace():
        s += 1
    while e > s and raw[e - 1].isspace():
        e -= 1
    return s, e


# Cue tường thuật/sự kiện bên trong ngoặc — KHÁC với ngoặc là 1 phần tên (brand, đồng nghĩa).
# Xem docs/ANNOTATION_GUIDELINE.md §3.2: "prograf (dose decreased...)" loại, "Rosuvastatin
# (Crestor)" giữ nguyên vì không có động từ mô tả sự kiện bên trong.
_NARRATIVE_CUE = re.compile(
    r"\b(decreased|increased|changed|discontinued|started|stopped|switched|held|"
    r"đang dùng|đã dùng|giảm liều|tăng liều|ngừng|bắt đầu|quyết định|chuyển sang|tiền sử)\b",
    re.IGNORECASE,
)


def _trim_narrative_paren(raw: str, s: int, e: int) -> int:
    """Cắt đuôi span (CHẨN_ĐOÁN/THUỐC) nếu kết thúc bằng ngoặc tường thuật. Trả end mới.

    2 trường hợp (đều đo được trong exp_0022 predictions):
    (a) ngoặc MỞ nhưng KHÔNG đóng trong span — luôn cắt, đây là artifact cắt ngang cửa sổ/dòng,
        không bao giờ là biên hợp lệ. VD: "Bệnh thận đa nang (tiền sử" -> "Bệnh thận đa nang".
    (b) ngoặc đã ĐÓNG ở cuối span, nội dung bên trong có cue tường thuật -> cắt.
        VD: "prograf (dose decreased from 5mg bid to 1mg bid)" -> "prograf".
        KHÔNG cắt nếu nội dung không có cue (brand/đồng nghĩa): "Rosuvastatin (Crestor)" giữ nguyên.
    """
    text = raw[s:e]
    open_idx = text.rfind("(")
    if open_idx < 0:
        return e
    close_idx = text.rfind(")")
    if close_idx < open_idx:  # (a) chưa đóng trong span
        e2 = s + open_idx
    elif _NARRATIVE_CUE.search(text[open_idx + 1:close_idx]):  # (b) đã đóng, có cue
        e2 = s + open_idx
    else:
        return e
    while e2 > s and raw[e2 - 1] in " \t":
        e2 -= 1
    return e2 if e2 > s else e


def _is_garbage(text: str, typ: str) -> bool:
    t = text.strip()
    if len(t) < 2:
        return True
    if normalize_for_match(t) in _STOPSPANS:
        return True
    # span thuần số/dấu chỉ hợp lệ cho KẾT_QUẢ_XÉT_NGHIỆM
    if typ != TYPE_KQ_XN and re.fullmatch(r"[\d\W]+", t):
        return True
    return False


def _section_map(raw: str):
    """Trả list (line_start, line_end, top_section) để tra section_top theo offset."""
    spans = []
    top = None
    for line, lstart in _iter_lines(raw):
        norm = normalize_for_match(line)
        hdr = _match_header(norm)
        label_m = _LABEL.match(line)
        if hdr and not label_m:
            nt, _ = hdr
            if nt:
                top = nt
        spans.append((lstart, lstart + len(line), top))
    return spans


def _top_at(section_spans, offset: int) -> Optional[str]:
    for s, e, top in section_spans:
        if s <= offset <= e:
            return top
    return None


class NERExtractor:
    def __init__(self, model_dir="models/ner_xlmr", maxlen: int = 256, stride: int = 48,
                 batch_size: int = 16, min_conf: float = 0.6, split_newlines: bool = True):
        self.model_dir = str(_ROOT / model_dir) if not Path(model_dir).is_absolute() else model_dir
        self.maxlen = maxlen
        self.stride = stride
        self.batch_size = batch_size
        self.min_conf = min_conf  # bỏ span độ tin thấp (chống mảnh vụn/rác)
        # split_newlines=False tái lập exp_0003 (chạy TRƯỚC khi _split_newlines ra đời).
        # Bằng chứng BTC: text/assert KHÔNG phụ thuộc matcher candidate, nên chênh lệch
        # exp_0003(28.63/31.03) vs exp_0007(27.77/30.14) chỉ có thể do _split_newlines
        # -> nó làm TỤT cả text lẫn assert (~0.9 mỗi cái).
        self.split_newlines = split_newlines
        self._tok = None
        self._model = None
        self._device = None

    def load(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        self._tok = AutoTokenizer.from_pretrained(self.model_dir)
        self._model = AutoModelForTokenClassification.from_pretrained(self.model_dir)
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self._device).eval()
        return self

    def extract(self, raw: str) -> List[Mention]:
        import torch
        if not raw.strip():
            return []
        enc = self._tok(
            raw, truncation=True, max_length=self.maxlen, stride=self.stride,
            return_overflowing_tokens=True, return_offsets_mapping=True,
            padding=True, return_tensors="pt",
        )
        offsets_all = enc.pop("offset_mapping")
        enc.pop("overflow_to_sample_mapping", None)
        input_ids = enc["input_ids"].to(self._device)
        attention = enc["attention_mask"].to(self._device)

        spans = []
        with torch.no_grad():
            for i in range(0, input_ids.size(0), self.batch_size):
                logits = self._model(
                    input_ids=input_ids[i:i + self.batch_size],
                    attention_mask=attention[i:i + self.batch_size],
                ).logits
                sm = torch.softmax(logits, dim=-1)
                conf, pred = sm.max(-1)
                pred = pred.cpu().tolist()
                conf = conf.cpu().tolist()
                for j in range(len(pred)):
                    offs = offsets_all[i + j].tolist()
                    spans += token_labels_to_char_spans(offs, pred[j], conf[j])

        # lọc rác + độ tin thấp, snap biên theo từ, rồi giải chồng lấn greedy theo conf
        section_spans = _section_map(raw)
        cand = []
        seen = set()
        for sp in spans:
            if sp["conf"] < self.min_conf:
                continue
            # tách span vượt dòng -> mỗi dòng 1 khái niệm cùng type
            pieces = (_split_newlines(raw, sp["position"][0], sp["position"][1])
                      if self.split_newlines else [tuple(sp["position"])])
            for s0, e0 in pieces:
                s, e = _snap_word(raw, s0, e0)
                if e <= s:
                    continue
                if sp["type"] in (TYPE_CHAN_DOAN, TYPE_THUOC):
                    e = _trim_narrative_paren(raw, s, e)
                    if e <= s:
                        continue
                text = raw[s:e]
                if not text.strip() or _is_garbage(text, sp["type"]):
                    continue
                key = (sp["type"], s, e)
                if key in seen:
                    continue
                seen.add(key)
                cand.append((sp["conf"], s, e, sp["type"], text))

        # greedy: nhận span conf cao trước, bỏ span CHỒNG LẤN với span đã nhận (mọi type)
        cand.sort(key=lambda x: (-x[0], -(x[2] - x[1])))
        accepted = []
        for conf, s, e, typ, text in cand:
            if any(s < ae and e > as_ for _, as_, ae, _, _ in accepted):
                continue
            accepted.append((conf, s, e, typ, text))

        mentions = [Mention(text, typ, s, e, _top_at(section_spans, s), None)
                    for conf, s, e, typ, text in sorted(accepted, key=lambda x: x[1])]
        return mentions
