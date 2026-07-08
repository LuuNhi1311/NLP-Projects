# -*- coding: utf-8 -*-
"""
benchmark.py — Hàm ĐO & SO SÁNH cho benchmark (không phụ thuộc I/O).

Tách câu:  so sánh 2 phương pháp qua thống kê + độ đồng thuận ranh giới.
NER     :  so sánh 2 phương pháp qua số thực thể/nhãn + độ trùng khớp span.

Lưu ý: đây là so sánh PHƯƠNG PHÁP-với-PHƯƠNG PHÁP (chưa có gold chuẩn) —
đúng mục tiêu "áp dụng công cụ & chốt phương pháp", không khẳng định độ chính xác.
Phần seqeval (nếu có gold nhỏ) minh hoạ CÁCH đo P/R/F1.
"""
from __future__ import annotations
import statistics as st


# --------------------------------------------------------------------------- #
# Tách câu
# --------------------------------------------------------------------------- #
def seg_stats(sentences: list[str], runtime: float) -> dict:
    lens = [len(s) for s in sentences] or [0]
    return {
        "n_sentences": len(sentences),
        "total_chars": sum(lens),
        "avg_len": round(st.mean(lens), 1),
        "median_len": st.median(lens),
        "min_len": min(lens),
        "max_len": max(lens),
        "runtime_s": round(runtime, 3),
    }


def _boundaries(paragraphs: list[str], seg_fn) -> set[tuple[int, int]]:
    """Tập ranh giới CẮT (para_idx, offset) do một phương pháp tạo ra.

    Cả 2 phương pháp phân hoạch đoạn KHÍT (nối lại == đoạn gốc, đã kiểm chứng),
    nên offset = độ dài luỹ tích → so khớp ranh giới chính xác."""
    bounds = set()
    for pi, para in enumerate(paragraphs):
        sents = seg_fn([para])
        pos = 0
        for s in sents[:-1]:              # bỏ ranh giới cuối đoạn (đoạn nào cũng có)
            pos += len(s)
            bounds.add((pi, pos))
    return bounds


def seg_agreement(paragraphs: list[str], seg_a, seg_b) -> dict:
    """Đồng thuận ranh giới giữa 2 phương pháp (Jaccard + độ bao phủ)."""
    A = _boundaries(paragraphs, seg_a)
    B = _boundaries(paragraphs, seg_b)
    inter = A & B
    union = A | B
    return {
        "boundaries_A": len(A),
        "boundaries_B": len(B),
        "shared": len(inter),
        "jaccard": round(len(inter) / len(union), 3) if union else 1.0,
        "A_covered_by_B": round(len(inter) / len(A), 3) if A else 1.0,
        "B_covered_by_A": round(len(inter) / len(B), 3) if B else 1.0,
    }


# --------------------------------------------------------------------------- #
# NER
# --------------------------------------------------------------------------- #
def ner_stats(per_sentence_entities: list[list[dict]], runtime: float) -> dict:
    from collections import Counter
    by_label = Counter()
    uniq = set()
    total = 0
    for ents in per_sentence_entities:
        for e in ents:
            by_label[e["label"]] += 1
            uniq.add((e["text"], e["label"]))
            total += 1
    return {
        "total_entities": total,
        "unique_entities": len(uniq),
        "by_label": dict(by_label),
        "runtime_s": round(runtime, 3),
    }


def ner_agreement(ents_a: list[list[dict]], ents_b: list[list[dict]]) -> dict:
    """So khớp span giữa 2 phương pháp trên CÙNG tập câu."""
    exact = partial = 0
    total_a = total_b = 0
    label_match = 0
    for ea, eb in zip(ents_a, ents_b):
        total_a += len(ea)
        total_b += len(eb)
        set_a = {(e["start"], e["end"], e["label"]) for e in ea}
        for e in eb:
            key = (e["start"], e["end"], e["label"])
            if key in set_a:
                exact += 1
            else:
                # trùng vị trí (chồng lấn) bất kể nhãn?
                for a in ea:
                    if not (e["end"] <= a["start"] or e["start"] >= a["end"]):
                        partial += 1
                        if a["label"] == e["label"]:
                            label_match += 1
                        break
    return {
        "entities_A": total_a,
        "entities_B": total_b,
        "exact_match": exact,
        "overlap_not_exact": partial,
        "overlap_same_label": label_match,
    }


# --------------------------------------------------------------------------- #
# seqeval (minh hoạ đo P/R/F1 nếu có gold)
# --------------------------------------------------------------------------- #
def to_bio(sent_len: int, entities: list[dict]) -> list[str]:
    tags = ["O"] * sent_len
    for e in sorted(entities, key=lambda x: x["start"]):
        s, t, lb = e["start"], e["end"], e["label"]
        if s >= sent_len:
            continue
        tags[s] = f"B-{lb}"
        for i in range(s + 1, min(t, sent_len)):
            tags[i] = f"I-{lb}"
    return tags


def seqeval_report(gold: list[dict], pred_entities: list[list[dict]]) -> str:
    """gold: [{sentence, entities:[{start,end,label}]}], pred: list song song."""
    from seqeval.metrics import classification_report
    y_true, y_pred = [], []
    for g, pe in zip(gold, pred_entities):
        n = len(g["sentence"])
        y_true.append(to_bio(n, g["entities"]))
        y_pred.append(to_bio(n, pe))
    return classification_report(y_true, y_pred, digits=3, zero_division=0)
