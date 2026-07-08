# -*- coding: utf-8 -*-
"""
export_entities.py — Xuất NER ra file PHẲNG "chỉ value" (CSV / JSON), dễ đọc/soát.

Từ các file _ner*.json (mặc định *_ner.hybrid.json) sinh ra:
  1. <chương>_ner.hybrid.csv        — mỗi DÒNG = 1 thực thể: sentence_id, text, label
  2. HCH_006_entities_all.csv       — gộp cả sách (thêm cột chapter)
  3. HCH_006_entities_unique.csv    — thực thể DUY NHẤT: text, label, count (đã dedup)
  4. <chương>_ner.hybrid.values.json — mảng phẳng [{"text","label"}] (thuần value)

CSV ghi bằng utf-8-sig để Excel mở chữ Hán không lỗi.

Chạy:
    python export_entities.py                    # dùng *_ner.hybrid.json
    python export_entities.py --which ner        # dùng *_ner.json (gazetteer)
    python export_entities.py --which ner.model  # dùng *_ner.model.json
"""
from __future__ import annotations
import sys, json, csv, argparse
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[1] / "output" / "HCH_006"


def write_csv(path: Path, header: list[str], rows: list[list]):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="ner.hybrid",
                    help="hậu tố file nguồn: ner.hybrid | ner | ner.model")
    args = ap.parse_args()

    src = sorted(OUT.glob(f"*/*_{args.which}.json"))
    if not src:
        print(f"Không thấy file *_{args.which}.json trong {OUT}"); return

    all_rows = []                      # [chapter, sentence_id, text, label]
    uniq = Counter()                   # (text,label) -> count
    for p in src:
        chapter = p.parent.name        # HCH_006_001
        recs = json.loads(p.read_text(encoding="utf-8"))

        per_ent_rows = []              # [sentence_id, text, label]
        values = []                    # [{"text","label"}]
        for r in recs:
            for e in r["entities"]:
                per_ent_rows.append([r["sentence_id"], e["text"], e["label"]])
                all_rows.append([chapter, r["sentence_id"], e["text"], e["label"]])
                values.append({"text": e["text"], "label": e["label"]})
                uniq[(e["text"], e["label"])] += 1

        # (1) CSV phẳng mỗi chương
        csv_path = p.with_suffix(".csv")
        write_csv(csv_path, ["sentence_id", "text", "label"], per_ent_rows)
        # (4) JSON thuần value mỗi chương
        val_path = p.with_name(p.stem + ".values.json")
        val_path.write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {chapter}: {len(per_ent_rows):5d} thực thể → {csv_path.name} · {val_path.name}")

    # (2) CSV gộp cả sách
    all_path = OUT / f"HCH_006_entities_{args.which.replace('.', '_')}_all.csv"
    write_csv(all_path, ["chapter", "sentence_id", "text", "label"], all_rows)

    # (3) CSV thực thể duy nhất (dedup) — sắp theo label rồi count giảm dần
    uniq_rows = sorted(([t, l, c] for (t, l), c in uniq.items()),
                       key=lambda x: (x[1], -x[2], x[0]))
    uniq_path = OUT / f"HCH_006_entities_{args.which.replace('.', '_')}_unique.csv"
    write_csv(uniq_path, ["text", "label", "count"], uniq_rows)

    print(f"\n  gộp cả sách : {len(all_rows)} dòng → {all_path.name}")
    print(f"  duy nhất    : {len(uniq_rows)} thực thể → {uniq_path.name}")
    by_label = Counter(l for _, l, _ in uniq_rows)
    print("  theo nhãn (unique):", dict(by_label))


if __name__ == "__main__":
    main()
