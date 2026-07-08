# -*- coding: utf-8 -*-
"""
run_hybrid.py — Pipeline NER HỢP NHẤT (Hybrid D+A) + đánh giá.

Chạy:
    python run_hybrid.py                 # 2 chương sample, eval gold + sinh _ner.hybrid.json
    python run_hybrid.py --fast          # 120 câu đầu mỗi chương (nhanh)

Sinh ra (output/HCH_006/):
    HCH_006_00X/HCH_006_00X_ner.hybrid.json   ← NER hợp nhất (đủ 6 nhãn)
    HYBRID_REPORT.md                          ← seqeval A vs D vs Hybrid + phân rã nguồn A/D
"""
from __future__ import annotations
import sys, json, time, argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import ner as nerlib
import benchmark as bm
import eval_demo
from classical_ner import HFCharTagger, upos_map, HybridNER, CLASSICAL_REPO

ROOT = Path(__file__).resolve().parents[1]
GAZ  = ROOT / "gazetteer"
OUT  = ROOT / "output" / "HCH_006"
GOLD = ROOT / "gold" / "HCH_006_gold_demo.json"
LABELS = ["PER", "LOC", "ORG", "TITLE", "TME", "NUM"]


def load_chapter_sents(chapter_id: str) -> list[str]:
    p = OUT / chapter_id / f"{chapter_id}_seg.tsv"
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        if "\t" in ln:
            out.append(ln.split("\t", 1)[1])
    return out


def counts(per_sent, key="label") -> dict:
    c = Counter()
    for ents in per_sent:
        for e in ents:
            c[e[key]] += 1
    return dict(c)


def micro_line(rep: str) -> str:
    for l in rep.splitlines():
        if "micro avg" in l:
            return l.strip()
    return "(n/a)"


def ner_json(sids, sents, per_sent) -> str:
    recs = [{"sentence_id": sid, "sentence": s,
             "entities": nerlib.entities_public(ents)}
            for sid, s, ents in zip(sids, sents, per_sent)]
    return json.dumps(recs, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--chapters", nargs="+", default=["HCH_006_001", "HCH_006_002"])
    args = ap.parse_args()

    print("■ Nạp: rule [A] + classical [D] → Hybrid…")
    hybrid = HybridNER(GAZ)
    rule = hybrid.rule                                  # dùng lại
    cls = HFCharTagger(CLASSICAL_REPO, upos_map)        # D đứng riêng để so sánh

    md = ["# BÁO CÁO HYBRID NER (D+A) — cổ văn 文言文 (元史 卷001+002)\n",
          "> **[D] `roberta-classical-chinese`** lo **PER/LOC** ⊕ **[A] gazetteer+regex** lo "
          "**TME/NUM/TITLE/ORG**. Hợp nhất span theo ưu tiên + làm sạch ranh giới model.\n"]

    # ================= (1) seqeval gold: A vs D vs Hybrid =================
    print("\n■ (1) seqeval trên gold team (PER/TME/LOC)…")
    gdata = json.loads(GOLD.read_text(encoding="utf-8"))["sentences"]
    gold = [{"sentence": d["sentence"],
             "entities": eval_demo.attach_offsets(d["sentence"], d["entities"])} for d in gdata]
    gs = [d["sentence"] for d in gdata]

    variants = [("A rule", rule.tag), ("D classical", cls.tag), ("Hybrid D+A", hybrid.tag)]
    md += ["\n## (1) seqeval P/R/F1 — GOLD team (7 câu; PER/TME/LOC)\n",
           "> Gold nhỏ → minh hoạ. Mục tiêu: Hybrid ≥ max(A,D) trên micro-F1.\n\n",
           "| Công cụ | micro-P | micro-R | micro-F1 |\n|---|---|---|---|\n"]
    reps = {}
    for name, fn in variants:
        pred = [fn(s) for s in gs]
        rep = bm.seqeval_report(gold, pred); reps[name] = rep
        ml = micro_line(rep).split()
        p, r, f = ml[2], ml[3], ml[4]
        print(f"  [{name:12s}] P={p} R={r} F1={f}")
        md.append(f"| {name} | {p} | {r} | **{f}** |\n")
    for name in reps:
        md.append(f"\n<details><summary>{name} — chi tiết</summary>\n\n```\n{reps[name]}\n```\n</details>\n")

    # ================= (2) chạy Hybrid trên toàn tập + sinh json =================
    print("\n■ (2) Chạy Hybrid trên toàn tập sample + sinh _ner.hybrid.json…")
    md += [f"\n## (2) Kết quả trên tập sample + phân rã nguồn\n"]
    grand_src = Counter()
    grand_lbl = Counter()
    for ch in args.chapters:
        sents = load_chapter_sents(ch)
        if args.fast:
            sents = sents[:120]
        sids = [f"{ch}_{i:06d}" for i in range(1, len(sents) + 1)]
        t0 = time.time(); hy = hybrid.tag_many(sents); dt = time.time() - t0

        # so sánh với gazetteer-only hiện có (_ner.json)
        old_path = OUT / ch / f"{ch}_ner.json"
        old_n = 0
        if old_path.exists():
            old_n = sum(len(r["entities"]) for r in json.loads(old_path.read_text(encoding="utf-8")))

        outp = OUT / ch / f"{ch}_ner.hybrid.json"
        outp.write_text(ner_json(sids, sents, hy), encoding="utf-8")

        lbl = counts(hy, "label"); src = counts(hy, "src")
        grand_lbl.update(lbl); grand_src.update(src)
        print(f"  {ch}: {sum(lbl.values())} thực thể (A={src.get('A',0)}, D={src.get('D',0)}) "
              f"| gazetteer-only cũ={old_n} | {dt:.1f}s → {outp.name}")
        md.append(f"\n### {ch} ({len(sents)} câu)\n"
                  f"- Hybrid: **{sum(lbl.values())} thực thể** — {lbl}\n"
                  f"- Nguồn: **[A] rule = {src.get('A',0)}**, **[D] classical = {src.get('D',0)}** "
                  f"(D bổ sung tên ngoài từ điển)\n"
                  f"- Gazetteer-only cũ (`_ner.json`): {old_n} thực thể "
                  f"→ Hybrid thêm {sum(lbl.values())-old_n:+d}\n")

    md.append(f"\n**Tổng 2 chương:** {sum(grand_lbl.values())} thực thể — {dict(grand_lbl)}  \n"
              f"Nguồn: [A] rule = {grand_src.get('A',0)}, [D] classical = {grand_src.get('D',0)}\n")

    # ================= (3) định tính =================
    demo = [
        "太祖法天啟運聖武皇帝，諱鐵木真，姓奇渥溫氏，蒙古部人。",
        "以耶律楚材為中書令，粘合重山為左丞相，鎮海為右丞相。",
        "三年辛卯春二月，克鳳翔，攻洛陽、河中諸城，下之。",
        "命速不台等圍南京，金主遣其弟曹王訛可入質。",
    ]
    md.append("\n## (3) Định tính — Hybrid tag gì (nguồn A/D in kèm)\n")
    for s in demo:
        ents = hybrid.tag(s)
        txt = " · ".join(f"{e['text']}/{e['label']}({e['src']})" for e in ents) or "—"
        md.append(f"\n**{s}**\n\n> {txt}\n")

    md.append("""
## Nhận xét
- **Hybrid gộp điểm mạnh:** PER/LOC lấy từ [D] (bắt tên Mông Cổ ngoài từ điển),
  TME/NUM/TITLE/ORG lấy từ [A] (span sạch, đúng ranh giới đề). Ranh giới của [D] đã
  làm sạch (cắt 諱/姓/為… đầu span; bỏ đơn-ký-tự tôn hiệu như 帝/武/天).
- **[D] bổ sung** phần lớn PER/LOC mà gazetteer-only bỏ sót → recall tăng mạnh.
- **Còn lại cần bản final:** một số PER đơn-ký-tự nhiễu của [D] và biên TITLE ghép
  tên vẫn nên chốt trong guideline; fine-tune GuwenBERT/SikuBERT trên gold 300–500 câu
  sẽ nâng thêm precision.
""")
    rp = OUT / "HYBRID_REPORT.md"
    rp.write_text("".join(md), encoding="utf-8")
    print(f"\n✔ Đã lưu báo cáo: {rp}")


if __name__ == "__main__":
    main()
