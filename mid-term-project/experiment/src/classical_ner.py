# -*- coding: utf-8 -*-
"""
classical_ner.py — Công cụ NER CỔ VĂN native + pipeline HỢP NHẤT (Hybrid D+A).

- HFCharTagger : token-classification char-level cho model cổ văn phồn thể
                 (KHÔNG cần OpenCC). Dùng cho roberta-classical-chinese & guwen-ner.
- upos_map / guwenner_map : map nhãn model → nhãn đề bài.
- HybridNER   : **[D] classical lo PER/LOC + [A] rule lo TME/NUM/TITLE/ORG**, hợp nhất
                span theo ưu tiên, làm sạch ranh giới của model.

Cơ sở kết luận benchmark (output/HCH_006/TOOLS_COMPARISON.md):
  · PER/LOC  → model cổ văn [D] mạnh nhất (bắt tên Mông Cổ 拖雷/耶律楚材/斡難河…).
  · TME/NUM  → rule [A] gộp span sạch (model [D] cắt vụn 三年辛卯春二月).
  · TITLE/ORG→ gazetteer + hậu tố [A] (model [D] không sinh 2 nhãn này).
"""
from __future__ import annotations
from pathlib import Path


# --------------------------------------------------------------------------- #
# Tagger tổng quát cho model CỔ VĂN (char-level, native phồn thể → KHÔNG OpenCC)
# --------------------------------------------------------------------------- #
class HFCharTagger:
    def __init__(self, repo: str, label_fn, merge_labels=("PER", "LOC")):
        import torch
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(repo)
        self.mdl = AutoModelForTokenClassification.from_pretrained(repo).eval()
        self.id2 = self.mdl.config.id2label
        self.label_fn = label_fn
        self.merge = set(merge_labels)

    def _decode(self, sent, offs, ids):
        spans, cur = [], None
        for (a, b), i in zip(offs, ids):
            if a == b:                          # special/padding token
                cur = None; continue
            proj, begin = self.label_fn(self.id2[int(i)])
            if proj is None:
                cur = None; continue
            cont = cur and cur["label"] == proj and (proj in self.merge or not begin)
            if cont:
                cur["end"] = b
            else:
                cur = {"start": a, "end": b, "label": proj}
                spans.append(cur)
        return [{"text": sent[s["start"]:s["end"]], "label": s["label"],
                 "start": s["start"], "end": s["end"]} for s in spans]

    def tag_many(self, sents, batch_size=16):
        out = []
        for i in range(0, len(sents), batch_size):
            batch = sents[i:i + batch_size]
            enc = self.tok(batch, return_offsets_mapping=True, return_tensors="pt",
                           padding=True, truncation=True, max_length=510)
            offs = enc.pop("offset_mapping")
            with self.torch.no_grad():
                logits = self.mdl(**enc).logits
            ids = logits.argmax(-1)
            for j, sent in enumerate(batch):
                out.append(self._decode(sent, offs[j].tolist(), ids[j].tolist()))
        return out

    def tag(self, sent):
        return self.tag_many([sent])[0]


def upos_map(raw: str):
    """UPOS cổ văn → nhãn đề bài. Trả (proj_label|None, is_begin)."""
    begin = raw.startswith("B-")
    r = raw[2:] if raw[:2] in ("B-", "I-") else raw
    if r.startswith("PROPN"):
        if ("NameType=Geo" in r) or ("NameType=Nat" in r) or ("Case=Loc" in r):
            return "LOC", begin
        return "PER", begin                     # Prs/Sur/Giv
    if r.startswith("NOUN") and "Case=Tem" in r:
        return "TME", begin
    if r.startswith("NUM"):
        return "NUM", begin
    return None, begin


def guwenner_map(raw: str):
    """guwen-ner NOUN_BOOKNAME/NOUN_OTHER → 'ENT' (chỉ phát hiện danh từ riêng)."""
    begin = raw.startswith("B-")
    r = raw[2:] if raw[:2] in ("B-", "I-") else raw
    if r in ("NOUN_OTHER", "NOUN_BOOKNAME"):
        return "ENT", begin
    return None, begin


CLASSICAL_REPO = "KoichiYasuoka/roberta-classical-chinese-base-upos"


# --------------------------------------------------------------------------- #
# Hợp nhất span
# --------------------------------------------------------------------------- #
def resolve(sent, cands):
    """Chọn tham lam KHÔNG chồng lấn: ưu tiên priority cao → span dài → trái sang."""
    cands = sorted(cands, key=lambda c: (-c[3], -(c[1] - c[0]), c[0]))
    taken = [False] * (len(sent) + 1)
    out = []
    for s, e, label, pri, src in cands:
        if any(taken[s:e]):
            continue
        for i in range(s, e):
            taken[i] = True
        out.append({"text": sent[s:e], "label": label, "start": s, "end": e, "src": src})
    out.sort(key=lambda x: x["start"])
    return out


# ký tự HAY dính đầu span của model (động từ/hư từ/mẫu 諱X, 姓X) → cắt bỏ
STRIP_PREFIX = set("諱姓曰為命遣攻克圍獲以于於與及會遂率次立置敕詔封拜授征討伐幸賜號")
# đơn-ký-tự PER/LOC hay là NHIỄU (tôn hiệu/đại từ) → loại nếu span dài 1
DROP1 = set("帝武天聖神文英睿孝之其也者乎焉后王公子母兄弟父弟氏部")


class HybridNER:
    """[D] classical (PER/LOC) ⊕ [A] rule (TME/NUM/TITLE/ORG)."""
    NAME = "Hybrid D+A"

    def __init__(self, gaz_dir: Path, classical_repo: str = CLASSICAL_REPO):
        import ner as nerlib
        self.rule = nerlib.RuleNER(gaz_dir)
        self.cls = HFCharTagger(classical_repo, upos_map)

    @staticmethod
    def _is_han(ch: str) -> bool:
        o = ord(ch)
        return 0x3400 <= o <= 0x9FFF or 0x20000 <= o <= 0x2FA1F

    def _clean(self, sent, e):
        """Làm sạch span model → trả LIST span con (tách tại ký tự KHÔNG phải chữ Hán:
        dấu liệt kê 、, ngoặc 校勘 （X）〔Y〕…) + cắt 諱/姓/為… đầu + bỏ đơn-ký-tự nhiễu."""
        s, t = e["start"], e["end"]
        while s < t and sent[s] in STRIP_PREFIX:
            s += 1
        out, i = [], s
        while i < t:
            if not self._is_han(sent[i]):
                i += 1; continue
            j = i
            while j < t and self._is_han(sent[j]):
                j += 1
            if not (j - i == 1 and sent[i] in DROP1):       # bỏ đơn-ký-tự tôn hiệu/hư từ
                out.append({"start": i, "end": j, "label": e["label"]})
            i = j
        return out

    def _merge(self, sent, rule_ents, cls_ents):
        cands = []
        # [A] rule: sở hữu TME/NUM/TITLE/ORG (pri 5); PER từ điển rất chắc (pri 4);
        #           LOC hậu tố dễ nhầm (粘合重山→LOC) → pri thấp, chỉ lấp chỗ D bỏ trống.
        for e in rule_ents:
            lab = e["label"]
            if lab in ("TME", "NUM", "TITLE", "ORG"):
                cands.append((e["start"], e["end"], lab, 5, "A"))
            elif lab == "PER":
                cands.append((e["start"], e["end"], "PER", 4, "A"))
            elif lab == "LOC":
                cands.append((e["start"], e["end"], "LOC", 1, "A"))
        # [D] classical: PER/LOC (pri 3) — bắt tên ngoài từ điển
        for e in cls_ents:
            if e["label"] not in ("PER", "LOC"):
                continue
            for ce in self._clean(sent, e):
                cands.append((ce["start"], ce["end"], ce["label"], 3, "D"))
        return resolve(sent, cands)

    def tag(self, sent):
        return self._merge(sent, self.rule.tag(sent), self.cls.tag(sent))

    def tag_many(self, sents, batch_size=16):
        rule_all = [self.rule.tag(s) for s in sents]
        cls_all = self.cls.tag_many(sents, batch_size=batch_size)
        return [self._merge(s, r, c) for s, r, c in zip(sents, rule_all, cls_all)]
