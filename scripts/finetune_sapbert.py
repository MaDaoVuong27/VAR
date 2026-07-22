# -*- coding: utf-8 -*-
"""Fine-tune SapBERT song ngữ trên cặp tên từ KB (khối candidate, hướng B / IDEAS_2 §3.1).

VÌ SAO: SapBERT gốc train trên UMLS tiếng Anh → bắt đúng "đại khái bệnh gì" nhưng CHỌN NHẦM
mã cụ thể trên tiếng Việt (đo được: 'Suy tim...' → F20.2 tâm thần phân liệt; 'viêm họng do
liên cầu' → A54.5 lậu cầu). Fine-tune trên cặp (tên_VN ↔ tên_EN) cùng mã → kéo các cách gọi
CÙNG khái niệm lại gần nhau trong không gian vector. Dữ liệu song song có sẵn trong KB.

CÁCH LÀM: in-batch InfoNCE (contrastive). Batch N cặp (a_i, b_i) là synonym cùng mã; embed
tất cả a, b (CLS + normalize — KHỚP HỆT inference sapbert.py); ma trận cosine; cross-entropy
để a_i khớp b_i, negatives = mọi b_j khác trong batch. Đối xứng 2 chiều.

⚠️ Pooling PHẢI khớp inference (CLS token, max_length 32, normalize) — nếu lệch thì embedding
train vô dụng cho index. (Cùng loại bug với sliding-window ở train_ner.)

Usage:
    python scripts/finetune_sapbert.py --out models/sapbert_ft --epochs 2 --bs 64
"""
import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.common.text_norm import normalize_for_match  # noqa: E402

_ICD = ROOT / "knowledge_base" / "icd10" / "processed" / "icd10_vn.csv"
_RXN = ROOT / "knowledge_base" / "rxnorm" / "processed" / "rxnorm_terms.csv"
_BASE = "cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR"


def build_pairs(max_rxn_pairs: int, seed: int):
    """Cặp positive (name_a, name_b) = 2 cách gọi CÙNG 1 mã. Trả list (a,b)."""
    rng = random.Random(seed)
    pairs = []

    # ICD: (tên VN, tên EN) cùng mã — dữ liệu song song lõi
    with open(_ICD, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("ma_benh") or "").strip()
            vi = (row.get("ten_benh_vi") or "").strip()
            en = (row.get("disease_name_en") or "").strip()
            if code and vi and en and normalize_for_match(vi) != normalize_for_match(en):
                pairs.append((vi, en))
            # tên cấp nhóm 3 ký tự (VN↔EN) — thêm vocab y khoa song ngữ (khái niệm cha)
            nvi = (row.get("ten_nhom_3ky_tu_vi") or "").strip()
            nen = (row.get("nhom_3ky_tu_name_en") or "").strip()
            if nvi and nen and normalize_for_match(nvi) != normalize_for_match(nen) and rng.random() < 0.15:
                pairs.append((nvi, nen))
    n_icd = len(pairs)

    # RxNorm: synonym trong cùng rxcui (brand ↔ ingredient ↔ clinical drug)
    by_cui = defaultdict(set)
    with open(_RXN, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rx = (row.get("rxcui") or "").strip()
            s = (row.get("str") or "").strip()
            if rx and s:
                by_cui[rx].add(s)
    rxn_pairs = []
    for cui, names in by_cui.items():
        names = list(names)
        if len(names) < 2:
            continue
        rng.shuffle(names)
        # tối đa 3 cặp/rxcui để không lệ thuộc rxcui nhiều synonym
        for i in range(min(3, len(names) - 1)):
            rxn_pairs.append((names[i], names[i + 1]))
    rng.shuffle(rxn_pairs)
    rxn_pairs = rxn_pairs[:max_rxn_pairs]
    pairs += rxn_pairs

    rng.shuffle(pairs)
    print(f"[pairs] ICD song ngữ: {n_icd} | RxNorm synonym: {len(rxn_pairs)} | tổng: {len(pairs)}")
    return pairs


def mine_hard_negatives(pairs, tok, model, dev, maxlen, k, seed):
    """Với mỗi cặp (a,b), tìm k tên gần a nhất trong pool NHƯNG là cặp khác → hard negative.

    ⚠️ Đây là thứ in-batch negative ngẫu nhiên KHÔNG dạy được (batch-acc→1.0 vì negative
    quá xa). Hard negative = mã gần giống nhưng khác → ép model học ĐÚNG RANH GIỚI
    (vd 'viêm họng do liên cầu' J02 phải tách khỏi 'viêm họng do lậu cầu' A54).
    """
    import torch, torch.nn.functional as F, numpy as np, faiss
    names = [a for a, _ in pairs]  # dùng vế a (thường là tên VN) làm anchor pool
    embs = []
    model.eval()
    with torch.no_grad():
        for i in range(0, len(names), 512):
            batch = [normalize_for_match(t) for t in names[i:i + 512]]
            t = tok(batch, padding=True, truncation=True, max_length=maxlen, return_tensors="pt").to(dev)
            e = F.normalize(model(**t).last_hidden_state[:, 0], dim=-1)
            embs.append(e.cpu().numpy().astype(np.float32))
    embs = np.vstack(embs)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    _, nbr = index.search(embs, k + 6)  # +buffer để loại chính nó
    model.train()
    hard = []
    for i in range(len(names)):
        hn = [names[j] for j in nbr[i] if j != i][:k]
        while len(hn) < k:
            hn.append(names[(i + 1) % len(names)])  # phòng hờ đủ số
        hard.append(hn)
    return hard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=_BASE)
    ap.add_argument("--out", default="models/sapbert_ft")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--temp", type=float, default=0.05, help="nhiệt độ InfoNCE")
    ap.add_argument("--max-rxn-pairs", type=int, default=40000)
    ap.add_argument("--maxlen", type=int, default=32, help="KHỚP inference sapbert.py")
    ap.add_argument("--hard-k", type=int, default=0,
                    help="số hard negative/anchor (0 = chỉ in-batch ngẫu nhiên như v1 thất bại). Đề xuất 3-5.")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModel

    torch.manual_seed(args.seed)
    pairs = build_pairs(args.max_rxn_pairs, args.seed)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModel.from_pretrained(args.base).to(dev).train()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)

    def encode(texts):
        # KHỚP HỆT _Encoder.encode của sapbert.py: normalize -> CLS -> F.normalize
        batch = [normalize_for_match(t) for t in texts]
        t = tok(batch, padding=True, truncation=True, max_length=args.maxlen,
                return_tensors="pt").to(dev)
        cls = model(**t).last_hidden_state[:, 0]
        return F.normalize(cls, dim=-1)

    hard = None
    if args.hard_k > 0:
        print(f"[hard-neg] mining {args.hard_k} hard negative/anchor bằng SapBERT gốc...")
        hard = mine_hard_negatives(pairs, tok, model, dev, args.maxlen, args.hard_k, args.seed)
        print(f"[hard-neg] xong. Ví dụ: anchor '{pairs[0][0][:30]}' -> hard negs {[h[:20] for h in hard[0][:3]]}")

    n_steps = int(len(pairs) / args.bs * args.epochs)
    print(f"[train] {len(pairs)} cặp, bs={args.bs}, {args.epochs} epoch = {n_steps} steps, "
          f"hard_k={args.hard_k}, dev={dev}")
    idx = list(range(len(pairs)))
    rng = random.Random(args.seed)
    step = 0
    for ep in range(int(args.epochs) + 1):
        rng.shuffle(idx)
        for i in range(0, len(idx), args.bs):
            if step >= n_steps:
                break
            chunk = idx[i:i + args.bs]
            if len(chunk) < 2:
                continue
            N = len(chunk)
            a = [pairs[j][0] for j in chunk]
            b = [pairs[j][1] for j in chunk]
            ea, eb = encode(a), encode(b)
            labels = torch.arange(N, device=dev)
            if hard is not None:
                # thêm cột hard negative của TỪNG anchor -> negative KHÓ, không chỉ in-batch
                hn_flat = [h for j in chunk for h in hard[j]]     # N*K tên
                ehn = encode(hn_flat).view(N, args.hard_k, -1)   # (N,K,d)
                inbatch = ea @ eb.t()                            # (N,N)
                hard_sim = (ea.unsqueeze(1) * ehn).sum(-1)       # (N,K) anchor·hard-neg riêng
                logits = torch.cat([inbatch, hard_sim], dim=1) / args.temp  # (N, N+K)
                loss = F.cross_entropy(logits, labels)
            else:
                logits = ea @ eb.t() / args.temp
                loss = 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.t(), labels))
            opt.zero_grad()
            loss.backward()
            opt.step()
            step += 1
            if step % 100 == 0:
                acc = (logits.argmax(1) == labels).float().mean().item()
                print(f"  step {step}/{n_steps} | loss {loss.item():.4f} | batch-acc {acc:.3f}", flush=True)
        if step >= n_steps:
            break

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    model.eval()
    model.save_pretrained(out)
    tok.save_pretrained(out)
    print(f"[done] SapBERT fine-tuned -> {out}")
    print("Nhớ: rebuild FAISS index với model này (cache npz mới) trước khi eval.")


if __name__ == "__main__":
    main()
