# -*- coding: utf-8 -*-
"""
finalize_outputs.py — Gom output về ĐÚNG 2 FILE CSV / chương (giống định dạng tsv).

Mỗi chương sinh:
  HCH_006_00X_seg.csv   →  sentence_id, sentence            (từ _seg.tsv)
  HCH_006_00X_ner.csv   →  sentence_id, text, label         (từ _ner.hybrid.json, phẳng)

  python finalize_outputs.py            # chỉ sinh 2 CSV
  python finalize_outputs.py --clean    # sinh 2 CSV rồi XOÁ các file trung gian
                                        # (giữ: 2 CSV/chương + các report *.md)

CSV ghi utf-8-sig để Excel mở chữ Hán không lỗi.
"""
from __future__ import annotations
import sys, json, csv, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[1] / "output" / "HCH_006"


def write_csv(path: Path, header, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def build_csvs():
    chapters = []
    for cdir in sorted(p for p in OUT.iterdir() if p.is_dir()):
        ch = cdir.name
        tsv = cdir / f"{ch}_seg.tsv"
        ner = cdir / f"{ch}_ner.hybrid.json"
        if not tsv.exists() or not ner.exists():
            continue
        seg_rows = [ln.split("\t", 1) for ln in tsv.read_text(encoding="utf-8").splitlines() if "\t" in ln]
        write_csv(cdir / f"{ch}_seg.csv", ["sentence_id", "sentence"], seg_rows)
        recs = json.loads(ner.read_text(encoding="utf-8"))
        ent_rows = [[r["sentence_id"], e["text"], e["label"]] for r in recs for e in r["entities"]]
        write_csv(cdir / f"{ch}_ner.csv", ["sentence_id", "text", "label"], ent_rows)
        chapters.append(cdir)
        print(f"  {ch}: {len(seg_rows)} câu → {ch}_seg.csv | {len(ent_rows)} thực thể → {ch}_ner.csv")
    return chapters


def clean(chapters):
    """Giữ: 2 CSV/chương (_seg.csv,_ner.csv) + report *.md ở cấp thư mục. Xoá phần còn lại."""
    removed = 0
    for cdir in chapters:                       # trong mỗi chương chỉ giữ 2 CSV
        ch = cdir.name
        keep = {f"{ch}_seg.csv", f"{ch}_ner.csv"}
        for f in cdir.iterdir():
            if f.is_file() and f.name not in keep:
                f.unlink(); removed += 1
    for f in OUT.iterdir():                      # cấp thư mục: giữ report .md, xoá csv trung gian
        if f.is_file() and f.suffix.lower() != ".md":
            f.unlink(); removed += 1
    print(f"  đã xoá {removed} file trung gian (giữ 2 CSV/chương + *.md)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()
    chapters = build_csvs()
    if args.clean:
        clean(chapters)


if __name__ == "__main__":
    main()
