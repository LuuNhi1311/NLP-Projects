# -*- coding: utf-8 -*-
"""
bench_tools.py — SO SÁNH NHIỀU CÔNG CỤ NER cho văn ngôn 文言文 (phồn thể).

Mục tiêu (để họp team & CHỐT công cụ): trên tập sample 元史 卷001+002, so sánh
5 hướng NER, trả lời "công cụ nào tối ưu độ chính xác & ưu chuộng chữ Hán cổ?".

Công cụ đưa vào so sánh
-----------------------
  [A] rule      — Gazetteer + regex (baseline offline, đủ 6 nhãn)              [ner.RuleNER]
  [B] cluener   — BERT CLUENER (giản thể hiện đại) + OpenCC 繁→简             [ner.ModelNER]
  [C] ckip      — BERT ckiplab NER (phồn thể hiện đại, OntoNotes)             [ner.ModelNER]
  [D] guwen-cls — roberta-classical-chinese-UPOS (CỔ VĂN native) → map nhãn   [HFCharTagger]
  [E] guwen-ner — ethanyt/guwen-ner (CỔ VĂN native, chỉ phát hiện DANH TỪ RIÊNG)

[D],[E] huấn luyện THẲNG trên cổ văn phồn thể → KHÔNG cần OpenCC.

Đo lường
--------
  1) seqeval P/R/F1 trên GOLD của team (7 câu, nhãn PER/TME/LOC) — có gold thực.
  2) Bao phủ (coverage): số thực thể/ nhãn mỗi công cụ tìm được trên TOÀN tập sample
     (proxy cho recall, không cần gold) + đồng thuận exact-span với baseline rule.
  3) Định tính: dump song song vài câu tiêu biểu (tên Mông Cổ, mốc thời gian).

Chạy:  python bench_tools.py            (mặc định 2 chương đã tách câu ở output/)
       python bench_tools.py --fast     (chỉ 120 câu đầu mỗi chương cho nhanh)
"""
from __future__ import annotations
import sys, json, time, argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import ner as nerlib
import benchmark as bm
from classical_ner import HFCharTagger, upos_map, guwenner_map

ROOT = Path(__file__).resolve().parents[1]
GAZ  = ROOT / "gazetteer"
OUT  = ROOT / "output" / "HCH_006"
GOLD = ROOT / "gold" / "HCH_006_gold_demo.json"
LABELS = ["PER", "LOC", "ORG", "TITLE", "TME", "NUM"]


# --------------------------------------------------------------------------- #
def load_chapter_sents(chapter_id: str) -> list[str]:
    p = OUT / chapter_id / f"{chapter_id}_seg.tsv"
    sents = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        if "\t" in ln:
            sents.append(ln.split("\t", 1)[1])
    return sents


def per_label_counts(per_sent) -> dict:
    c = Counter()
    for ents in per_sent:
        for e in ents:
            c[e["label"]] += 1
    return dict(c)


def agree_exact(pred, ref) -> int:
    """số span (start,end,label) của pred trùng KHÍT với ref (cùng tập câu)."""
    n = 0
    for pe, re in zip(pred, ref):
        rset = {(e["start"], e["end"], e["label"]) for e in re}
        for e in pe:
            if (e["start"], e["end"], e["label"]) in rset:
                n += 1
    return n


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="chỉ 120 câu đầu mỗi chương")
    ap.add_argument("--chapters", nargs="+", default=["HCH_006_001", "HCH_006_002"])
    args = ap.parse_args()

    md = ["# SO SÁNH CÔNG CỤ NER — cổ văn 文言文 (元史 卷001+002)\n",
          "> Trả lời câu hỏi họp team: *công cụ nào tối ưu độ chính xác & ưu chuộng chữ Hán cổ?*\n",
          "\n## Công cụ đưa vào so sánh\n",
          "| Mã | Công cụ | Loại | Cổ văn? | OpenCC |\n|---|---|---|---|---|\n",
          "| A | Gazetteer + regex | luật/từ điển | — | không |\n",
          "| B | BERT CLUENER | học sâu, TQ **hiện đại giản thể** | ✗ | **cần** |\n",
          "| C | ckiplab BERT NER | học sâu, TQ **hiện đại phồn thể** | ✗ | không |\n",
          "| D | roberta-**classical**-chinese UPOS→map | học sâu, **CỔ VĂN native** | ✓ | không |\n",
          "| E | ethanyt/**guwen-ner** | học sâu, **CỔ VĂN** (chỉ dò danh từ riêng) | ✓ | không |\n"]

    # ------------------ khởi tạo công cụ ------------------
    print("■ Nạp công cụ…")
    tools = {}
    tools["A rule"] = nerlib.RuleNER(GAZ)
    def wrap_model(key):                       # ModelNER dùng tag_many
        m = nerlib.ModelNER(key); return m
    try: tools["B cluener"] = wrap_model("cluener")
    except Exception as e: print("  [B] fail:", e)
    try: tools["C ckip"] = wrap_model("ckip")
    except Exception as e: print("  [C] fail:", e)
    try:
        tools["D guwen-cls"] = HFCharTagger(
            "KoichiYasuoka/roberta-classical-chinese-base-upos", upos_map)
    except Exception as e: print("  [D] fail:", e)
    try:
        tools["E guwen-ner"] = HFCharTagger(
            "ethanyt/guwen-ner", guwenner_map, merge_labels=("ENT",))
    except Exception as e: print("  [E] fail:", e)
    print("  → công cụ sẵn sàng:", ", ".join(tools))

    def run(tool, sents):
        if hasattr(tool, "tag_many"):
            return tool.tag_many(sents)
        return [tool.tag(s) for s in sents]

    # ==================================================================== #
    # 1) seqeval trên GOLD của team (PER/TME/LOC)
    # ==================================================================== #
    print("\n■ (1) seqeval trên gold team…")
    import eval_demo
    gdata = json.loads(GOLD.read_text(encoding="utf-8"))["sentences"]
    gold = [{"sentence": d["sentence"],
             "entities": eval_demo.attach_offsets(d["sentence"], d["entities"])} for d in gdata]
    gsents = [d["sentence"] for d in gdata]

    md += ["\n## (1) seqeval P/R/F1 — GOLD team (7 câu; nhãn PER/TME/LOC)\n",
           "> Gold nhỏ, chỉ có PER/TME/LOC → CHỈ minh hoạ. Bản final: gold 300–500 câu, đủ 6 nhãn.\n",
           "> [E] guwen-ner không phân loại nhãn nên KHÔNG đưa vào bảng này (xem mục 2 & 3).\n"]
    for name, tool in tools.items():
        if name.startswith("E"):
            continue
        pred = run(tool, gsents)
        rep = bm.seqeval_report(gold, pred)
        micro = [l for l in rep.splitlines() if "micro avg" in l]
        print(f"  [{name}] {micro[0].strip() if micro else '(n/a)'}")
        md.append(f"\n### [{name}]\n```\n{rep}\n```\n")

    # ==================================================================== #
    # 2) Bao phủ trên TOÀN tập sample + đồng thuận với rule
    # ==================================================================== #
    print("\n■ (2) Bao phủ trên toàn tập sample…")
    all_sents = []
    for ch in args.chapters:
        s = load_chapter_sents(ch)
        all_sents += (s[:120] if args.fast else s)
    print(f"  tổng {len(all_sents)} câu")

    preds, timings = {}, {}
    for name, tool in tools.items():
        t0 = time.time(); preds[name] = run(tool, all_sents); timings[name] = time.time() - t0
        print(f"  [{name}] {timings[name]:6.1f}s  counts={per_label_counts(preds[name])}")

    ref = preds["A rule"]
    md += [f"\n## (2) Bao phủ trên toàn tập sample ({len(all_sents)} câu)\n",
           "> Số thực thể tìm được / nhãn = **proxy cho recall** (chưa trừ sai). "
           "‘khớp rule’ = span+nhãn trùng KHÍT baseline A.\n\n",
           "| Công cụ | tổng | " + " | ".join(LABELS) + " | khớp rule | thời gian |\n",
           "|---|---|" + "---|" * len(LABELS) + "---|---|\n"]
    for name in tools:
        c = per_label_counts(preds[name])
        tot = sum(c.values())
        ag = "—" if name.startswith("A") else str(agree_exact(preds[name], ref))
        row = [str(c.get(l, 0)) for l in LABELS]
        md.append(f"| {name} | {tot} | " + " | ".join(row) + f" | {ag} | {timings[name]:.1f}s |\n")

    # ==================================================================== #
    # 3) Định tính — dump vài câu tiêu biểu
    # ==================================================================== #
    print("\n■ (3) Định tính…")
    demo = [
        "太祖法天啟運聖武皇帝，諱鐵木真，姓奇渥溫氏，蒙古部人。",
        "以耶律楚材為中書令，粘合重山為左丞相，鎮海為右丞相。",
        "三年辛卯春二月，克鳳翔，攻洛陽、河中諸城，下之。",
        "命速不台等圍南京，金主遣其弟曹王訛可入質。",
    ]
    md.append("\n## (3) Định tính — cùng câu, các công cụ tag gì\n")
    for s in demo:
        md.append(f"\n**{s}**\n\n| Công cụ | thực thể |\n|---|---|\n")
        for name, tool in tools.items():
            ents = tool.tag(s)
            txt = " · ".join(f"{e['text']}/{e['label']}" for e in ents) or "—"
            md.append(f"| {name} | {txt} |\n")

    # ------------------ khuyến nghị ------------------
    md.append("""
## Khuyến nghị chốt (để họp team)

**Kết luận: không một công cụ đơn nào tối ưu cả 6 nhãn. Chốt HỢP NHẤT (hybrid).**

1. **PER / LOC (phần khó nhất, ăn điểm nhất) → model CỔ VĂN native [D]
   `roberta-classical-chinese`.** Đây là công cụ *ưu chuộng chữ Hán cổ* nhất:
   huấn luyện thẳng trên 文言文 **phồn thể** (UD_Classical_Chinese) → **KHÔNG cần
   OpenCC**, và bắt được **tên Mông Cổ phiên âm** (拖雷, 耶律楚材, 斡難河…) mà
   model TQ hiện đại [B]/[C] bỏ sót hoặc cắt sai.
2. **TME / NUM → RULE [A].** Model cổ văn cắt *vụn* mốc thời gian ghép
   (二年庚寅春正月 → 4 mảnh); regex gộp span sạch, đúng ranh giới đề bài.
3. **TITLE / ORG → gazetteer [A] + hậu tố** (省/軍/院/使…). Model UPOS không sinh
   trực tiếp 2 nhãn này.
4. **[E] guwen-ner** dùng làm *bộ dò danh từ riêng* để **tăng recall & soát sót**
   cho [A]/[D] (nó chỉ nói "đây là danh từ riêng", không phân loại).
5. **[B] CLUENER hiện đại** → chỉ giữ làm *đối chứng “công cụ sai miền”* trong report
   (minh chứng vì sao KHÔNG dùng NLP tiếng Trung hiện đại cho cổ văn).

**Bản FINAL:** fine-tune encoder cổ văn (GuwenBERT/SikuBERT) trên gold 300–500 câu +
GuNER2023, rồi vẫn **hợp nhất TME/NUM từ luật**. [D] là baseline “ready-to-run” rất
mạnh để đối chiếu mức tăng sau fine-tune.
""")

    outp = OUT / "TOOLS_COMPARISON.md"
    outp.write_text("".join(md), encoding="utf-8")
    print(f"\n✔ Đã lưu báo cáo: {outp}")


if __name__ == "__main__":
    main()
