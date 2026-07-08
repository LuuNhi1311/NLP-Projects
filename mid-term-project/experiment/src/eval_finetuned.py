# -*- coding: utf-8 -*-
"""
eval_finetuned.py — Đánh giá model FINE-TUNE (GuwenBERT/C-CLUE) + so sánh.

So trên GOLD 7 câu (seqeval) + đếm coverage toàn tập:
  · Hybrid          (_ner.csv)                — đủ 6 nhãn
  · Fine-tuned      (HCH_ner.finetuned.csv)   — PER/LOC/ORG/TITLE
  · Hybrid+FT (ghép): PER/LOC/ORG/TITLE từ FT + TME/NUM từ Hybrid
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "HCH_006"
GOLD = ROOT / "gold" / "HCH_006_gold_demo.json"
CHAPTERS = ["HCH_006_001", "HCH_006_002"]
FROM_MODEL = {"PER", "LOC", "ORG", "TITLE"}


def load_csv(path) -> dict:
    d = defaultdict(list)
    if not path.exists():
        return d
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        d[r["sentence_id"]].append((r["text"], r["label"]))
    return d


def to_bio(sent: str, ents) -> list:
    tags = ["O"] * len(sent)
    used = [False] * len(sent)
    for text, label in sorted(ents, key=lambda e: -len(e[0])):   # span dài đặt trước
        start = 0
        while True:
            idx = sent.find(text, start)
            if idx < 0:
                break
            if not any(used[idx:idx + len(text)]):
                for k in range(idx, idx + len(text)):
                    used[k] = True
                tags[idx] = "B-" + label
                for k in range(idx + 1, idx + len(text)):
                    tags[k] = "I-" + label
                break
            start = idx + 1
    return tags


# ---- nạp dữ liệu ----
hybrid, finet = defaultdict(list), defaultdict(list)
for ch in CHAPTERS:
    for sid, v in load_csv(OUT / ch / f"{ch}_ner.csv").items():          hybrid[sid] = v
    for sid, v in load_csv(OUT / ch / "HCH_ner.finetuned.csv").items():  finet[sid] = v

# Hybrid+FT: PER/LOC/ORG/TITLE từ FT, TME/NUM (và phần khác) từ Hybrid
hybrid_ft = defaultdict(list)
for sid in set(hybrid) | set(finet):
    hybrid_ft[sid] = [(t, l) for (t, l) in hybrid[sid] if l not in FROM_MODEL] + \
                     [(t, l) for (t, l) in finet[sid] if l in FROM_MODEL]

METHODS = {"Hybrid (Ⓓ+Ⓐ)": hybrid, "Fine-tune (C-CLUE)": finet, "Hybrid+FT": hybrid_ft}

# ---- seqeval trên gold ----
from seqeval.metrics import classification_report, precision_score, recall_score, f1_score
gold = json.loads(GOLD.read_text(encoding="utf-8"))["sentences"]

print("■ seqeval trên GOLD 7 câu (nhãn gold: PER/TME/LOC)\n")
rows_md = []
for name, preds in METHODS.items():
    yt, yp = [], []
    for g in gold:
        s = g["sentence"]
        yt.append(to_bio(s, [(e["text"], e["label"]) for e in g["entities"]]))
        yp.append(to_bio(s, preds.get(g["sentence_id"], [])))
    P, R, F = precision_score(yt, yp), recall_score(yt, yp), f1_score(yt, yp)
    # per-label PER / LOC
    rep = classification_report(yt, yp, digits=3, zero_division=0, output_dict=True)
    per = rep.get("PER", {}); loc = rep.get("LOC", {})
    print(f"[{name}] micro P={P:.3f} R={R:.3f} F1={F:.3f} | "
          f"PER F1={per.get('f1-score',0):.3f} | LOC F1={loc.get('f1-score',0):.3f}")
    rows_md.append((name, P, R, F, per.get("f1-score", 0), loc.get("f1-score", 0)))

# ---- coverage toàn tập ----
print("\n■ Coverage toàn tập (597 câu) theo nhãn\n")
cov = {}
for name, preds in METHODS.items():
    c = Counter(l for ents in preds.values() for _, l in ents)
    cov[name] = c
    print(f"[{name}] tổng={sum(c.values())}  {dict(c)}")

# ---- xuất bảng markdown để chèn report ----
LB = ["PER", "LOC", "ORG", "TITLE", "TME", "NUM"]
md = ["\n---\n## Đánh giá bổ sung: model FINE-TUNE (GuwenBERT trên C-CLUE)\n",
      "> Model fine-tune trên **C-CLUE** (二十四史, cùng miền) — sinh **PER/LOC/ORG/TITLE**. "
      "TME/NUM lấy từ rule (bản **Hybrid+FT** ghép đủ 6 nhãn).\n",
      "\n### seqeval trên gold 7 câu\n",
      "| Phương pháp | micro-P | micro-R | micro-F1 | PER F1 | LOC F1 |\n|---|---|---|---|---|---|\n"]
for name, P, R, F, pf, lf in rows_md:
    md.append(f"| {name} | {P:.3f} | {R:.3f} | **{F:.3f}** | {pf:.3f} | {lf:.3f} |\n")
md.append("\n### Coverage toàn tập (597 câu)\n| Phương pháp | tổng | " + " | ".join(LB) + " |\n|---|---|" + "---|" * len(LB) + "\n")
for name, c in cov.items():
    md.append(f"| {name} | {sum(c.values())} | " + " | ".join(str(c.get(l, 0)) for l in LB) + " |\n")

(OUT / "FINETUNE_EVAL.md").write_text("".join(md), encoding="utf-8")
print("\n✔ Bảng đã lưu: output/HCH_006/FINETUNE_EVAL.md")
