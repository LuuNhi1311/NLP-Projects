# -*- coding: utf-8 -*-
"""
eval_demo.py — MINH HOẠ đo P/R/F1 bằng seqeval trên GOLD MẪU.

Mục đích: cho nhóm thấy đầy đủ vòng "đo chất lượng NER" sẽ chạy thế nào khi có gold.
Gold hiện tại chỉ 7 câu (illustrative) → CON SỐ KHÔNG phải kết luận chính xác,
chỉ minh hoạ CƠ CHẾ. Bản final thay bằng gold 300-500 câu.

    python eval_demo.py
"""
from __future__ import annotations
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import ner as nerlib
import benchmark as bm

ROOT = Path(__file__).resolve().parents[1]
GAZ  = ROOT / "gazetteer"
GOLD = ROOT / "gold" / "HCH_006_gold_demo.json"
OUTMD = ROOT / "output" / "HCH_006" / "EVAL_seqeval_demo.md"


def attach_offsets(sentence: str, entities: list[dict]) -> list[dict]:
    """Gán offset cho entity gold theo text (find lần xuất hiện đầu)."""
    out, cursor = [], 0
    for e in entities:
        idx = sentence.find(e["text"])
        if idx < 0:
            continue
        out.append({"text": e["text"], "label": e["label"],
                    "start": idx, "end": idx + len(e["text"])})
    return out


def main():
    data = json.loads(GOLD.read_text(encoding="utf-8"))["sentences"]
    gold = [{"sentence": d["sentence"],
             "entities": attach_offsets(d["sentence"], d["entities"])} for d in data]
    sents = [d["sentence"] for d in data]

    n_ent = sum(len(g['entities']) for g in gold)
    print(f"■ Gold mẫu: {len(sents)} câu ({n_ent} thực thể)\n")
    md = [f"# Đo P/R/F1 bằng seqeval — GOLD MẪU (minh hoạ cơ chế)\n",
          f"> Gold **{len(sents)} câu / {n_ent} thực thể** — chỉ để demo CÁCH đo, "
          f"KHÔNG phải kết luận độ chính xác. Bản final: gold 300-500 câu.\n"]

    # [A] RuleNER
    rule = nerlib.RuleNER(GAZ)
    pred_a = [rule.tag(s) for s in sents]
    rep_a = bm.seqeval_report(gold, pred_a)
    print("===== [A] Gazetteer + regex — seqeval =====\n" + rep_a)
    md += ["## [A] Gazetteer + regex\n```\n" + rep_a + "\n```\n"]

    # [B] ModelNER (nếu có mạng/model)
    try:
        model = nerlib.ModelNER("cluener")
        pred_b = model.tag_many(sents)
        rep_b = bm.seqeval_report(gold, pred_b)
        print("===== [B] BERT (cluener) + OpenCC — seqeval =====\n" + rep_b)
        md += ["## [B] BERT (cluener) + OpenCC\n```\n" + rep_b + "\n```\n"]
    except Exception as ex:
        print(f"[B] bỏ qua (không nạp được model): {ex}")
        md += [f"## [B] BERT — bỏ qua: {ex}\n"]

    md.append("## Nhận định\n"
              "- [A] chính xác cao ở PER (trong từ điển) & TME, nhưng **recall PER thấp** "
              "(sót tên ngoài gazetteer) và **LOC yếu** (hậu tố không phủ 鳳翔/洛陽).\n"
              "- [B] **bắt LOC tốt**, nhưng fail PER (tên Mông Cổ) và **không có nhãn TME/NUM**.\n"
              "- → Hai công cụ **bổ sung**: final nên fine-tune encoder cổ văn + hợp nhất gazetteer "
              "(TME/NUM từ luật; PER/LOC/ORG từ model).\n")
    OUTMD.parent.mkdir(parents=True, exist_ok=True)
    OUTMD.write_text("\n".join(md), encoding="utf-8")
    print(f"\n✔ Đã lưu: {OUTMD}")

    # In chi tiết để soi định tính
    print("===== Chi tiết (gold vs [A]) =====")
    for d, pa in zip(data, pred_a):
        g = {(e["text"], e["label"]) for e in d["entities"]}
        p = {(e["text"], e["label"]) for e in pa}
        print(f"· {d['sentence']}")
        print(f"    gold: {sorted(g)}")
        print(f"    [A] : {sorted(p)}")


if __name__ == "__main__":
    main()
