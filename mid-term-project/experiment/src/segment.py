# -*- coding: utf-8 -*-
"""
segment.py — TÁCH CÂU (sentence segmentation) cho văn ngôn 文言文.

Cung cấp 2 PHƯƠNG PHÁP để benchmark:

  [A] rule-based (regex + máy trạng thái)
      - Cắt tại dấu câu kết thúc 。！？ , có nhận biết ngoặc thoại 「」/『』
        (không cắt bên trong lời thoại).
      - Ưu: nhanh, deterministic, offline, tận dụng dấu câu có sẵn.

  [B] Stanza — Classical Chinese ('lzh', dựa trên UD_Classical_Chinese)
      - Bộ tokenizer + sentence-segmenter học máy cho cổ văn.
      - Ưu: "công cụ chuẩn NLP", đối chứng với rule-based.

Cả 2 xử lý theo TỪNG ĐOẠN (paragraph) → ranh giới đoạn luôn là ranh giới câu.
"""
from __future__ import annotations
import regex as re

# Dấu kết thúc câu chính trong cổ văn
END_PUNCT = "。！？"
OPEN_Q  = "「『（〔"
CLOSE_Q = "」』）〕"


# --------------------------------------------------------------------------- #
# [A] Rule-based
# --------------------------------------------------------------------------- #
def segment_rule(paragraphs: list[str], split_semicolon: bool = False) -> list[str]:
    """Tách câu bằng luật. Trả về list câu (đã bỏ đoạn rỗng)."""
    enders = END_PUNCT + ("；" if split_semicolon else "")
    sentences: list[str] = []
    for para in paragraphs:
        buf: list[str] = []
        depth = 0                       # độ sâu ngoặc thoại
        for ch in para:
            buf.append(ch)
            if ch in OPEN_Q:
                depth += 1
            elif ch in CLOSE_Q:
                depth = max(0, depth - 1)
            elif ch in enders and depth == 0:
                # gộp luôn dấu đóng ngoặc/nháy ngay sau dấu kết câu nếu có
                sentences.append("".join(buf).strip())
                buf = []
        tail = "".join(buf).strip()
        if tail:                        # phần dư không có dấu kết câu
            sentences.append(tail)
    return [s for s in sentences if s]


# --------------------------------------------------------------------------- #
# [B] Stanza (Classical Chinese)
# --------------------------------------------------------------------------- #
_STANZA_NLP = None

def get_stanza(download: bool = True):
    """Khởi tạo (lazy) pipeline Stanza cho cổ văn lzh. Chỉ tokenize (đủ cho tách câu)."""
    global _STANZA_NLP
    if _STANZA_NLP is None:
        import stanza
        if download:
            stanza.download("lzh", processors="tokenize", verbose=False)
        _STANZA_NLP = stanza.Pipeline(
            "lzh", processors="tokenize", verbose=False, use_gpu=False,
        )
    return _STANZA_NLP


def segment_stanza(paragraphs: list[str], nlp=None) -> list[str]:
    """Tách câu bằng Stanza lzh (xử lý theo từng đoạn để giữ ranh giới đoạn)."""
    nlp = nlp or get_stanza()
    sentences: list[str] = []
    for para in paragraphs:
        if not para.strip():
            continue
        doc = nlp(para)
        for sent in doc.sentences:
            s = sent.text.strip()
            if s:
                sentences.append(s)
    return sentences


# --------------------------------------------------------------------------- #
# Xuất định dạng _seg.tsv
# --------------------------------------------------------------------------- #
def to_seg_tsv(sentences: list[str], chapter_id: str) -> str:
    """sentence_id \\t sentence, id dạng HCH_006_001_000001."""
    lines = []
    for i, s in enumerate(sentences, start=1):
        sid = f"{chapter_id}_{i:06d}"
        lines.append(f"{sid}\t{s}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys, time
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from clean import clean_book

    DATA = Path(__file__).resolve().parents[2] / "data"
    chapters = clean_book(DATA / "元史_full.txt")
    ch = chapters[0]                    # 卷001 太祖本紀
    print(f"Chương {ch.chapter_id}: {len(ch.paragraphs)} đoạn, {ch.clean_chars} ký tự\n")

    t0 = time.time()
    rule = segment_rule(ch.paragraphs)
    t1 = time.time()
    print(f"[A] Rule-based : {len(rule):4d} câu  ({t1-t0:.3f}s)")
    for s in rule[:3]:
        print("     •", s[:50])

    t0 = time.time()
    stz = segment_stanza(ch.paragraphs)
    t1 = time.time()
    print(f"\n[B] Stanza lzh : {len(stz):4d} câu  ({t1-t0:.1f}s)")
    for s in stz[:3]:
        print("     •", s[:50])
