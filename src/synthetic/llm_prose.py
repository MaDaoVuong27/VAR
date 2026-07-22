# -*- coding: utf-8 -*-
"""Synthetic Cấp 3 — LLM self-host sinh ghi chú lâm sàng văn xuôi (DATA_PLAN §Cấp 3).

VÌ SAO CẦN: template (Cấp 2, generate.py) cho nhãn chính xác 100% nhưng đa dạng ngữ cảnh
hạn chế — nó chỉ biết đúng số câu ta viết tay. Văn xuôi xen kẽ (sample 6/8/25/93 mà baseline
chết) là chỗ template yếu nhất. Cấp 3 bù đúng chỗ đó.

CÁCH LÀM (đảo ngược: chọn nhãn TRƯỚC, sinh text SAU):
  1. Ta CHỌN TRƯỚC danh sách entity (bệnh+mã ICD, thuốc+RxCUI, triệu chứng) + assertion.
  2. Yêu cầu LLM viết đoạn ghi chú tiếng Việt chứa NGUYÊN VĂN các cụm đó.
  3. Dò lại offset bằng tìm chuỗi trên text LLM sinh; entity nào không tìm thấy -> BỎ doc.
  → Nhãn biết sẵn vì entity do TA chọn, không phải do LLM tự nghĩ ra rồi ta đoán ngược.

TUÂN LUẬT (xem docs/DATA_PLAN.md §PHẦN 2 + docs/TASK_SPEC.md):
  - Model SELF-HOST (Qwen2.5-7B-Instruct, ~7.6B ≤ 9B), chạy LOCAL, KHÔNG gọi API ngoài.
  - Chỉ chạy LÚC SINH DATA, KHÔNG nằm trong pipeline inference (không cộng vào ngân sách
    inference; xem CONFIG_REFERENCE.md để biết tổng params lúc inference).
  - Entity lấy từ knowledge_base/*/processed/ (ICD-10 + RxNorm) — KB do chính đề chỉ định.
  - KHÔNG đọc data/raw/input/ (test BTC) ở bất kỳ bước nào.
  - Sinh có seed, nhưng LLM sampling KHÔNG tái tạo bit-exact -> phải NỘP KÈM file jsonl gốc
    (DATA_PLAN §PHẦN 2 điểm 1). Code này để BTC tham khảo quy trình.

Usage:
    python -m src.synthetic.llm_prose --n 1500 --out data/synthetic/prose.jsonl --seed 7
    # gộp với template rồi train:
    cat data/synthetic/train.jsonl data/synthetic/prose.jsonl > data/synthetic/train_mix.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import List

from .catalog import Catalog
from . import lexicons as LEX

_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # self-host, 7.6B ≤ 9B

SYSTEM = (
    "Bạn là bác sĩ lâm sàng người Việt. Bạn viết ghi chú bệnh án bằng tiếng Việt, "
    "văn phong ngắn gọn, tự nhiên như ghi chú thật trong bệnh viện."
)

# Prompt yêu cầu LLM DÙNG NGUYÊN VĂN cụm từ -> để dò lại offset được.
TEMPLATE = """Viết một đoạn ghi chú bệnh án tiếng Việt ({nsent} câu, văn xuôi liền mạch, KHÔNG dùng gạch đầu dòng, KHÔNG đánh số).

Đoạn ghi chú BẮT BUỘC chứa các cụm từ sau, giữ NGUYÊN VĂN từng ký tự, không dịch, không đổi thứ tự chữ, không thêm bớt chữ nào bên trong cụm:
{items}

Yêu cầu:
- Mỗi cụm xuất hiện ĐÚNG MỘT LẦN.
- Phần trong ngoặc là CHỈ DẪN NGỮ CẢNH cho bạn, KHÔNG được chép vào bài. Hãy diễn đạt ý
  đó bằng lời văn bác sĩ tự nhiên. (Sai: "bị phủ định đau ngực". Đúng: "không ghi nhận đau ngực".)
- Đặt mỗi cụm vào câu văn hoàn chỉnh, có chủ ngữ vị ngữ, đọc trôi chảy như bệnh án thật —
  KHÔNG liệt kê các cụm nối đuôi nhau bằng dấu phẩy.
- Chỉ trả về đoạn ghi chú, không giải thích, không tiêu đề, không nhắc lại yêu cầu.
"""

# ⚠️ Diễn đạt Ý NGHĨA, KHÔNG dùng thuật ngữ máy móc: đo được LLM chép thẳng chữ chỉ dẫn
# vào bài ("bị phủ định U lympho tế bào B" — không bác sĩ nào viết vậy), dạy NER pattern ma.
_CTX = {
    "isHistorical": "đã có TRONG QUÁ KHỨ, nay không còn cấp tính — dùng lối nói tự nhiên "
                    "như 'tiền sử', 'đã từng', 'trước đây', 'cách đây vài năm'",
    "isNegated": "bệnh nhân KHÔNG có điều này — dùng lối nói tự nhiên như 'không ghi nhận', "
                 "'chưa phát hiện', 'không có', 'loại trừ'",
    "isFamily": "là tình trạng của NGƯỜI NHÀ (bố/mẹ/anh/chị/em), KHÔNG phải của bệnh nhân",
}


# Danh pháp ICD trang trọng KHÔNG phải lời bác sĩ viết trong bệnh sử. Ép LLM nhồi nguyên văn
# "joint disorder, unspecified, lower leg" vào văn xuôi tiếng Việt -> câu hỏng, dạy NER sai.
# Prose chỉ lấy tên bệnh NGẮN, TIẾNG VIỆT, không có đuôi phân loại.
_FORMAL = re.compile(
    r"không xác định|không phân loại|chưa xác định|không đặc hiệu|phần khác|"
    r"nơi khác|các loại khác|khác và không|unspecified|other specified|"
    r", part |, level |NOS\b|\bNEC\b", re.IGNORECASE)


# Chỉ ký tự CÓ DẤU tiếng Việt. Dùng `ord(c)>127` là SAI: ký hiệu ICD như '†' trong
# "arthropathy in neoplastic disease (C00-D48†)" cũng >127 -> tên tiếng Anh lọt lưới (đã đo).
_VN_CHARS = re.compile(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợ"
                       r"ùúủũụưứừửữựỳýỷỹỵđ]", re.IGNORECASE)


def _is_natural_vi(name: str) -> bool:
    """Tên bệnh dùng được trong văn xuôi: tiếng Việt, ngắn, không đuôi phân loại ICD."""
    if _FORMAL.search(name):
        return False
    if not (1 <= len(name.split()) <= 6):
        return False
    if re.search(r"\(|\)|†|\*|[A-Z]\d{2}", name):  # ký hiệu/mã ICD lẫn trong tên
        return False
    return bool(_VN_CHARS.search(name))


def natural_diseases(cat: Catalog):
    pool = [d for d in cat.diseases if _is_natural_vi(d.text)]
    if not pool:
        raise SystemExit("[llm_prose] Không lọc được tên bệnh tự nhiên nào — kiểm tra icd10_vn.csv")
    return pool


def _plan(cat: Catalog, rng: random.Random, dis_pool=None):
    """Chọn TRƯỚC entity + assertion cho 1 doc. Trả list spec {text,type,assertions,candidates}."""
    specs = []
    pick_disease = (lambda: rng.choice(dis_pool)) if dis_pool else cat.disease

    def _assert(p_hist=0.35, p_neg=0.25, p_fam=0.05):
        a = []
        if rng.random() < p_hist:
            a.append("isHistorical")
        if rng.random() < p_neg:
            a.append("isNegated")
        if rng.random() < p_fam:
            a.append("isFamily")
        return a

    for _ in range(rng.randint(1, 3)):
        d = pick_disease()
        specs.append({"text": d.text, "type": "CHẨN_ĐOÁN",
                      "assertions": _assert(), "candidates": list(d.candidates)})
    for _ in range(rng.randint(1, 4)):
        specs.append({"text": cat.symptom(), "type": "TRIỆU_CHỨNG",
                      "assertions": _assert(p_hist=0.2, p_neg=0.35), "candidates": []})
    for _ in range(rng.randint(0, 2)):
        dr = cat.drug()
        txt = dr.text
        if rng.random() < 0.5:
            txt += " " + rng.choice(LEX.DRUG_DOSES)
        if rng.random() < 0.4:
            txt += " " + rng.choice(LEX.DRUG_ROUTES)
        specs.append({"text": txt, "type": "THUỐC",
                      "assertions": _assert(p_hist=0.5, p_neg=0.1), "candidates": list(dr.candidates)})
    for _ in range(rng.randint(0, 2)):
        specs.append({"text": cat.test(), "type": "TÊN_XÉT_NGHIỆM", "assertions": [], "candidates": []})

    # loại trùng text (mỗi cụm phải xuất hiện đúng 1 lần -> không cho 2 spec cùng chuỗi)
    seen, out = set(), []
    for s in specs:
        k = s["text"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    rng.shuffle(out)
    return out


def _prompt(specs, rng):
    lines = []
    for s in specs:
        ctx = [_CTX[a] for a in s["assertions"]]
        note = f" ({', '.join(ctx)})" if ctx else ""
        lines.append(f'- "{s["text"]}"{note}')
    return TEMPLATE.format(nsent=rng.randint(3, 7), items="\n".join(lines))


def _locate(text: str, specs, min_keep: float = 0.6):
    """Dò offset từng entity trên text LLM sinh. Trả (concepts, ok).

    ⚠️ HAI BÀI HỌC ĐO ĐƯỢC (bản đầu bỏ 100% doc, sinh ra file rỗng):

    1. **Khớp KHÔNG phân biệt hoa/thường**, và lấy chuỗi THẬT trong output làm nhãn.
       LLM hay viết thường chữ đầu tên bệnh ('Trứng cá đỏ' -> 'trứng cá đỏ'). Exact-match
       phân biệt hoa/thường làm mất entity, kéo theo bỏ cả doc. Nhãn `text` PHẢI là đúng
       chuỗi tại [start,end) của text sinh ra, nếu không offset sẽ vô nghĩa.

    2. **Giữ doc từng phần** thay vì all-or-nothing. Entity LLM không viết ra thì đơn giản
       là KHÔNG có trong text -> bỏ nó khỏi nhãn là ĐÚNG, không phải nhãn sai. Với ~8
       entity/doc, đòi hỏi cả 8 phải khớp là gần như chắc chắn hỏng.

    Span dài dò trước để 'ho khan' không bị 'ho' chiếm chỗ.
    """
    concepts, used = [], []
    for s in sorted(specs, key=lambda x: -len(x["text"])):
        start = -1
        for m in re.finditer(re.escape(s["text"]), text, re.IGNORECASE):
            if not any(m.start() < ue and m.end() > us for us, ue in used):
                start = m.start()
                break
        if start < 0:
            continue  # LLM không viết cụm này -> nó không có trong text -> bỏ nhãn là đúng
        end = start + len(s["text"])
        used.append((start, end))
        concepts.append({"text": text[start:end],  # chuỗi THẬT, không phải spec
                         "type": s["type"], "position": [start, end],
                         "assertions": s["assertions"], "candidates": s["candidates"]})
    if not concepts or len(concepts) / max(1, len(specs)) < min_keep:
        return None, False
    concepts.sort(key=lambda c: c["position"][0])
    return concepts, True


def _sweep_extra(text: str, concepts: List[dict], sweep_vocab, kb) -> int:
    """Gán nhãn cho entity LLM TỰ THÊM ngoài spec. Trả số nhãn thêm được.

    ⚠️ VÌ SAO BẮT BUỘC: LLM không chỉ viết đúng các cụm ta yêu cầu — nó còn tự nhắc bệnh/
    thuốc/triệu chứng khác ("bệnh gút đã điều trị bằng colchicine..."). Đo được **10% entity
    trong text prose không có nhãn** → train sẽ dạy NER rằng 'colchicine' là O, tức dạy
    THẲNG false-negative, hại đúng cái ta cần. Quét bù còn hơn bỏ mặc.

    Giới hạn đã biết: chỉ bắt được thứ có trong lexicon/RxNorm vocab; bệnh LLM tự nghĩ ra
    mà không khớp KB vẫn lọt. Assertion của entity quét bù để [] (không suy luận) — nhãn
    span/type đúng quan trọng hơn, và đoán assertion sai còn hại hơn để trống.
    """
    added = 0
    taken = [(c["position"][0], c["position"][1]) for c in concepts]

    def free(a, b):
        return not any(a < d and b > c for c, d in taken)

    for name, typ in sweep_vocab:
        for m in re.finditer(r"(?<![\wÀ-ỹ])" + re.escape(name) + r"(?![\wÀ-ỹ])", text, re.I):
            if not free(m.start(), m.end()):
                continue
            taken.append((m.start(), m.end()))
            concepts.append({"text": text[m.start():m.end()], "type": typ,
                             "position": [m.start(), m.end()], "assertions": [], "candidates": []})
            added += 1
    # thuốc: token khớp vocab RxNorm (ingredient/brand 1 token)
    for m in re.finditer(r"[A-Za-z][A-Za-z\-]{4,}", text):
        if not free(m.start(), m.end()) or not kb.is_drug_name(m.group(0)):
            continue
        taken.append((m.start(), m.end()))
        concepts.append({"text": m.group(0), "type": "THUỐC",
                         "position": [m.start(), m.end()], "assertions": [],
                         "candidates": kb.match_rxnorm(m.group(0), k=1)})
        added += 1
    concepts.sort(key=lambda c: c["position"][0])
    return added


def _clean(out: str) -> str:
    """Bỏ rác quanh đoạn LLM sinh (markdown, lời dẫn) — KHÔNG đụng nội dung."""
    out = out.strip()
    out = re.sub(r"^```[a-z]*\n?|```$", "", out).strip()
    out = re.sub(r"^(Đoạn ghi chú|Ghi chú|Trả lời)\s*:?\s*", "", out, flags=re.I).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--out", default="data/synthetic/prose.jsonl")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default=_MODEL)
    ap.add_argument("--batch", type=int, default=8, help="số prompt sinh cùng lúc")
    ap.add_argument("--max-new", type=int, default=420)
    ap.add_argument("--min-keep", type=float, default=0.6,
                    help="bỏ doc nếu tỉ lệ entity dò được offset < ngưỡng (0.6 = giữ doc có >=60%)")
    args = ap.parse_args()

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

    root = Path(__file__).resolve().parent.parent.parent
    cat = Catalog(seed=args.seed).load()
    rng = random.Random(args.seed)
    dis_pool = natural_diseases(cat)
    print(f"[llm_prose] tên bệnh dùng cho prose: {len(dis_pool)}/{len(cat.diseases)} "
          f"(đã lọc danh pháp ICD trang trọng + tên tiếng Anh)")

    from ..normalization import KnowledgeBase
    kb = KnowledgeBase().load()
    sweep_vocab = ([(s, "TRIỆU_CHỨNG") for s in LEX.SYMPTOMS_VI + LEX.SYMPTOMS_EN]
                   + [(s, "TÊN_XÉT_NGHIỆM") for s in LEX.TEST_NAMES])
    sweep_vocab.sort(key=lambda x: -len(x[0]))  # cụm dài trước ('ho khan' > 'ho')
    n_swept = 0

    # 4-bit: Qwen2.5-7B vừa 12GB VRAM (fp16 cần ~15GB -> không vừa RTX 3060)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                             bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(args.model, padding_side="left")
    model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=bnb,
                                                 device_map="cuda:0", dtype=torch.float16)
    model.eval()
    torch.manual_seed(args.seed)

    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept = dropped = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for i in range(0, args.n, args.batch):
            batch_specs = [_plan(cat, rng, dis_pool) for _ in range(min(args.batch, args.n - i))]
            prompts = [tok.apply_chat_template(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": _prompt(s, rng)}],
                tokenize=False, add_generation_prompt=True) for s in batch_specs]
            enc = tok(prompts, return_tensors="pt", padding=True).to("cuda:0")
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=args.max_new, do_sample=True,
                                     temperature=0.8, top_p=0.9,
                                     pad_token_id=tok.pad_token_id or tok.eos_token_id)
            for j, specs in enumerate(batch_specs):
                text = _clean(tok.decode(gen[j][enc["input_ids"].shape[1]:], skip_special_tokens=True))
                concepts, ok = _locate(text, specs, min_keep=args.min_keep)
                if not ok or not text.strip():
                    dropped += 1
                    continue
                n_swept += _sweep_extra(text, concepts, sweep_vocab, kb)
                # chốt an toàn: offset phải khớp tuyệt đối, nếu không thì bỏ
                if any(text[c["position"][0]:c["position"][1]] != c["text"] for c in concepts):
                    dropped += 1
                    continue
                f.write(json.dumps({"text": text, "concepts": concepts}, ensure_ascii=False) + "\n")
                kept += 1
            if (i // args.batch) % 5 == 0:
                print(f"  {i + len(batch_specs)}/{args.n} | giữ {kept} | bỏ {dropped}", flush=True)

    print(f"\nXong: giữ {kept}, bỏ {dropped} ({dropped / max(1, kept + dropped) * 100:.0f}% "
          f"— LLM không giữ nguyên văn cụm từ) -> {out_path}")
    print(f"Quét bù {n_swept} entity LLM tự thêm (nếu bỏ mặc, train sẽ dạy chúng là 'O').")
    print(f"README khi nộp: model={args.model} (self-host ≤9B, offline), seed={args.seed}. "
          f"LLM sampling KHÔNG tái tạo bit-exact -> NỘP KÈM file jsonl gốc này.")


if __name__ == "__main__":
    main()
