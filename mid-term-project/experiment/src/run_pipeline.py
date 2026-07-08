# -*- coding: utf-8 -*-
"""
run_pipeline.py — CHẠY TOÀN BỘ THỰC NGHIỆM trên tập sample.

Luồng:  clean → tách câu (2 pp) → NER (2 pp) → xuất file → benchmark → report.

Cách chạy:
    python run_pipeline.py                     # mặc định 元史 卷001, 卷002
    python run_pipeline.py --book 元史_full.txt --chapters 1 2
    python run_pipeline.py --no-model          # bỏ Method B (BERT) nếu không có mạng

Output (thư mục experiment/output/HCH_006/):
    HCH_006_00X/
        HCH_006_00X_seg.tsv          ← CANONICAL tách câu (rule-based)
        HCH_006_00X_seg.stanza.tsv   ← biến thể Stanza (để so sánh)
        HCH_006_00X_ner.json         ← CANONICAL NER (rule/gazetteer, đủ 6 nhãn)
        HCH_006_00X_ner.model.json   ← biến thể BERT+OpenCC (để so sánh)
        HCH_006_00X_annotations.txt  ← chú giải 〈〉 đã tách ra (không mất)
    BENCHMARK_REPORT.md              ← báo cáo so sánh tổng hợp
    benchmark_seg.csv / benchmark_ner.csv
"""
from __future__ import annotations
import sys, json, time, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from clean import clean_book
import segment as seg
import ner as nerlib
import benchmark as bm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parents[0] / "data"
GAZ  = ROOT / "gazetteer"
OUT  = ROOT / "output"


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ner_json(sentences, sids, per_sent_ents) -> str:
    records = []
    for sid, sent, ents in zip(sids, sentences, per_sent_ents):
        records.append({
            "sentence_id": sid,
            "sentence": sent,
            "entities": nerlib.entities_public(ents),
        })
    return json.dumps(records, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="元史_full.txt")
    ap.add_argument("--chapters", nargs="+", type=int, default=[1, 2])
    ap.add_argument("--no-model", action="store_true")
    ap.add_argument("--no-stanza", action="store_true")
    args = ap.parse_args()

    print(f"■ Bộ sử: {args.book}  |  chương: {args.chapters}")
    chapters = clean_book(DATA / args.book)
    book_code = chapters[0].book_code
    by_num = {c.chapter_num: c for c in chapters}
    targets = [by_num[n] for n in args.chapters if n in by_num]

    # khởi tạo công cụ nặng 1 lần
    rule_ner = nerlib.RuleNER(GAZ)
    model_ner = None
    if not args.no_model:
        print("■ Nạp model BERT NER (CLUENER + OpenCC)… (lần đầu tải ~400MB)")
        model_ner = nerlib.ModelNER("cluener")
    stanza_nlp = None
    if not args.no_stanza:
        print("■ Nạp Stanza lzh…")
        stanza_nlp = seg.get_stanza()

    seg_rows, ner_rows = [], []           # cho CSV/report
    report_blocks = []

    for ch in targets:
        cdir = OUT / book_code / ch.chapter_id
        print(f"\n=== {ch.chapter_id} (卷{ch.chapter_num}) — "
              f"{len(ch.paragraphs)} đoạn, {ch.clean_chars} ký tự ===")

        # ---------- TÁCH CÂU ----------
        t0 = time.time(); s_rule = seg.segment_rule(ch.paragraphs); t_rule = time.time()-t0
        s_stz, t_stz = [], 0.0
        if stanza_nlp is not None:
            t0 = time.time(); s_stz = seg.segment_stanza(ch.paragraphs, stanza_nlp); t_stz = time.time()-t0

        sids = [f"{ch.chapter_id}_{i:06d}" for i in range(1, len(s_rule)+1)]
        write(cdir / f"{ch.chapter_id}_seg.tsv", seg.to_seg_tsv(s_rule, ch.chapter_id))
        if s_stz:
            write(cdir / f"{ch.chapter_id}_seg.stanza.tsv", seg.to_seg_tsv(s_stz, ch.chapter_id))
        write(cdir / f"{ch.chapter_id}_annotations.txt",
              "\n".join(ch.annotations) + ("\n" if ch.annotations else ""))

        st_rule = bm.seg_stats(s_rule, t_rule)
        print(f"  tách câu [A rule]  : {st_rule['n_sentences']:4d} câu  "
              f"(avg {st_rule['avg_len']}) {t_rule:.3f}s")
        seg_rows.append({"chapter": ch.chapter_id, "method": "rule", **st_rule})
        seg_ag = {}
        if s_stz:
            st_stz = bm.seg_stats(s_stz, t_stz)
            print(f"  tách câu [B stanza]: {st_stz['n_sentences']:4d} câu  "
                  f"(avg {st_stz['avg_len']}) {t_stz:.1f}s")
            seg_rows.append({"chapter": ch.chapter_id, "method": "stanza", **st_stz})
            seg_ag = bm.seg_agreement(
                ch.paragraphs, seg.segment_rule,
                lambda ps: seg.segment_stanza(ps, stanza_nlp))
            print(f"  đồng thuận ranh giới: Jaccard={seg_ag['jaccard']}  "
                  f"rule⊂stanza={seg_ag['A_covered_by_B']}")

        # ---------- NER (chạy trên CÙNG tập câu rule-based) ----------
        t0 = time.time(); e_rule = [rule_ner.tag(s) for s in s_rule]; t_er = time.time()-t0
        write(cdir / f"{ch.chapter_id}_ner.json", ner_json(s_rule, sids, e_rule))
        stat_er = bm.ner_stats(e_rule, t_er)
        print(f"  NER [A gazetteer]  : {stat_er['total_entities']:4d} thực thể "
              f"{stat_er['by_label']}  {t_er:.3f}s")
        ner_rows.append({"chapter": ch.chapter_id, "method": "gazetteer", **stat_er})

        ner_ag = {}
        if model_ner is not None:
            t0 = time.time(); e_mdl = model_ner.tag_many(s_rule); t_em = time.time()-t0
            write(cdir / f"{ch.chapter_id}_ner.model.json", ner_json(s_rule, sids, e_mdl))
            stat_em = bm.ner_stats(e_mdl, t_em)
            print(f"  NER [B BERT+OpenCC]: {stat_em['total_entities']:4d} thực thể "
                  f"{stat_em['by_label']}  {t_em:.1f}s")
            ner_rows.append({"chapter": ch.chapter_id, "method": "bert_opencc", **stat_em})
            ner_ag = bm.ner_agreement(e_rule, e_mdl)
            print(f"  đồng thuận NER: exact={ner_ag['exact_match']}  "
                  f"overlap={ner_ag['overlap_not_exact']}")

        report_blocks.append(_chapter_block(ch, st_rule, seg_ag, stat_er, ner_ag,
                                            s_stz, model_ner is not None))

    # ---------- CSV + REPORT ----------
    _write_csv(OUT / book_code / "benchmark_seg.csv", seg_rows)
    _write_csv(OUT / book_code / "benchmark_ner.csv", ner_rows)
    _write_report(OUT / book_code / "BENCHMARK_REPORT.md", args, report_blocks)
    print(f"\n✔ Xong. Output tại: {OUT / book_code}")


# --------------------------------------------------------------------------- #
def _write_csv(path: Path, rows: list[dict]):
    import csv
    if not rows:
        return
    keys = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v)
                        for k, v in r.items()})


def _chapter_block(ch, st_rule, seg_ag, stat_er, ner_ag, s_stz, has_model) -> str:
    lines = [f"### {ch.chapter_id} (卷{ch.chapter_num})",
             f"- Sau cleaning: **{len(ch.paragraphs)} đoạn**, **{ch.clean_chars} ký tự**, "
             f"loại noise `{ch.removed}`, tách {len(ch.annotations)} chú 〈〉.",
             "",
             "**Tách câu**",
             f"- [A] rule-based: **{st_rule['n_sentences']} câu**, dài TB {st_rule['avg_len']} ký tự, {st_rule['runtime_s']}s"]
    if s_stz:
        lines.append(f"- [B] Stanza lzh: **{len(s_stz)} câu** (cắt vụn hơn); "
                     f"đồng thuận ranh giới Jaccard={seg_ag.get('jaccard')}, "
                     f"ranh giới rule ⊂ stanza = {seg_ag.get('A_covered_by_B')}")
    lines += ["", "**NER**",
              f"- [A] gazetteer+regex: **{stat_er['total_entities']} thực thể** — {stat_er['by_label']}"]
    if has_model and ner_ag:
        lines.append(f"- [B] BERT+OpenCC: **{ner_ag['entities_B']} thực thể**; "
                     f"khớp CHÍNH XÁC span+nhãn với [A] = {ner_ag['exact_match']}, "
                     f"chồng lấn khác = {ner_ag['overlap_not_exact']}")
    lines.append("")
    return "\n".join(lines)


def _write_report(path: Path, args, blocks: list[str]):
    header = f"""# BÁO CÁO BENCHMARK — Thực nghiệm tập sample

**Bộ sử:** `{args.book}`  |  **Chương sample:** {args.chapters}
**Mục tiêu:** minh hoạ CÁCH áp dụng công cụ cho *tách câu* và *NER* trên văn ngôn 文言文
(phồn thể), có benchmark để nhóm CHỐT phương pháp. (Không nhắm độ chính xác tuyệt đối.)

## Phương pháp đưa vào so sánh
| Tác vụ | [A] | [B] |
|---|---|---|
| Tách câu | Rule-based (regex, nhận biết 「」) | Stanza `lzh` (UD_Classical_Chinese) |
| NER | Gazetteer + regex (đủ 6 nhãn) | BERT `cluener` + OpenCC 繁→简 |

## Kết quả theo chương
"""
    tail = """
## Nhận định & khuyến nghị (để họp chốt)
- **Tách câu → chọn RULE-BASED.** Text đã có sẵn dấu câu 。！？ nên luật cho kết quả
  khớp đúng định nghĩa "câu" của đề (kết thúc bằng 。). Stanza `lzh` cắt ở mức *cụm/mệnh đề*
  (tách rời cả 諱|tên), số câu phình ~2–3× và **không khớp** format `_seg.tsv`. Stanza vẫn
  hữu ích như đối chứng và cho tokenize/POS nếu cần sau này.
- **NER → hai công cụ BỔ SUNG nhau, không thay thế:**
  - Gazetteer+regex: mạnh & nhất quán ở **TME, NUM, LOC/ORG theo hậu tố**, bắt PER/TITLE
    trong từ điển; điểm yếu là PER/LOC ngoài từ điển (đặc biệt tên Mông Cổ phiên âm).
  - BERT+OpenCC: bắt được **PER/LOC ngoài từ điển** nhưng **không có nhãn TME/NUM**, hay
    fragment tôn hiệu, và cần OpenCC (model huấn luyện trên hiện đại/giản thể).
  - → Hướng cho bản FINAL: **fine-tune encoder cổ văn (GuwenBERT/SikuBERT)** trên gold +
    **hợp nhất với gazetteer** (lấy TME/NUM từ luật, PER/LOC/ORG từ model).
- **繁/简:** OpenCC 繁→简 theo từng ký tự giữ căn lề 1-1 → map nhãn ngược về phồn thể chuẩn.

## File sinh ra mỗi chương
- `_seg.tsv` (canonical, rule-based) · `_seg.stanza.tsv` (đối chứng)
- `_ner.json` (canonical, gazetteer — đủ 6 nhãn) · `_ner.model.json` (đối chứng BERT)
- `_annotations.txt` (chú giải 〈〉 tách khỏi chính văn, giữ lại không mất)
"""
    write(path, header + "\n".join(blocks) + tail)


if __name__ == "__main__":
    main()
