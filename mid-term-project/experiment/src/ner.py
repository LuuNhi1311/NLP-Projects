# -*- coding: utf-8 -*-
"""
ner.py — NHẬN DẠNG THỰC THỂ (NER) cho văn ngôn 文言文.

Bộ nhãn (theo đề): PER, LOC, ORG, TITLE, TME, NUM.

2 PHƯƠNG PHÁP để benchmark:

  [A] RuleNER — GAZETTEER + REGEX  (baseline, offline, deterministic)
      - TME : 年號+數字+年, 干支, 季節/月, 元年 ...  (regex, ghép các TME liền kề)
      - NUM : 漢數字 (+餘/量詞)                        (regex)
      - LOC : hậu tố 州府縣河山城 ...                  (regex)
      - ORG : hậu tố 軍院省司臺衞 ...                  (regex)
      - TITLE: gazetteer 官職/爵 + hậu tố 使/尉         (gazetteer + regex)
      - PER : gazetteer nhân danh + mẫu 諱X / 姓X氏     (gazetteer + regex)

  [B] ModelNER — BERT token-classification + OpenCC  (mô hình học sâu)
      - OpenCC 繁→简 (giữ căn lề 1-1 để map offset ngược về phồn thể)
      - chạy pipeline transformers, map tagset của model → bộ nhãn đề bài
      - Mặc định: uer/roberta...cluener2020 (giản thể) → BẮT BUỘC OpenCC.

Đầu ra mỗi câu: list {text, label, start, end}.  (_ner.json chỉ giữ text+label)
"""
from __future__ import annotations
import regex as re
from pathlib import Path

LABELS = ["PER", "LOC", "ORG", "TITLE", "TME", "NUM"]

# --------------------------------------------------------------------------- #
# Bảng ký tự Hán số / can chi
# --------------------------------------------------------------------------- #
NUMCH = "一二三四五六七八九十百千萬万億兆零半兩两廿卅"
GAN   = "甲乙丙丁戊己庚辛壬癸"
ZHI   = "子丑寅卯辰巳午未申酉戌亥"
LOC_SUFFIX = "州府縣县郡路河山城嶺岭關关京都澤泽原陂谷川水海湖江嶽岳塞津渡峽峡"
ORG_SUFFIX = "軍军院省司臺台衞卫寺監监署閣阁坊"
NUM_MEASURE = "人匹乘級级里丈尺頃顷石斛斗柵栅騎骑鈞钧鎰镒級口枚艘"
# Động từ / giới từ / hư từ KHÔNG được là tiền tố của tên riêng (giảm lỗi ranh giới
# kiểu 攻陷同州→同州, 于斡難河→斡難河).
STOPCHARS = "之於于而以及與与則则即乃其此是為为攻陷破取圍围克復复守走奔逐入出至到會会遣使將将率屠拔還还渡度自從从"


# --------------------------------------------------------------------------- #
# [A] RuleNER — gazetteer + regex
# --------------------------------------------------------------------------- #
class RuleNER:
    def __init__(self, gaz_dir: Path):
        self.persons = self._load(gaz_dir / "person.txt")
        self.titles  = self._load(gaz_dir / "title.txt")
        self.nianhao = self._load(gaz_dir / "nianhao.txt")
        self._build_patterns()

    @staticmethod
    def _load(path: Path) -> list[str]:
        if not path.exists():
            return []
        out = []
        for ln in path.read_text(encoding="utf-8").splitlines():
            ln = ln.split("#", 1)[0].strip()
            if ln:
                out.append(ln)
        return out

    def _build_patterns(self):
        nh = "|".join(sorted(self.nianhao, key=len, reverse=True)) or r"(?!x)x"
        self.RE_TME = re.compile(
            rf"(?:(?:{nh})[{NUMCH}]+年)"                              # 至元三年
            rf"|(?:[{NUMCH}]+年)"                                     # 二十九年
            rf"|(?:元年)"
            rf"|(?:[{GAN}][{ZHI}])"                                   # 庚子
            rf"|(?:(?:春|夏|秋|冬)?閏?(?:正月|臘月|[{NUMCH}]{{1,3}}月))"  # 春正月/三月
        )
        self.RE_NUM = re.compile(
            rf"[{NUMCH}]+(?:餘|余)?(?:[{NUM_MEASURE}]|之眾|之衆)?"
        )
        # tiền tố = chữ Hán TRỪ nhóm động từ/hư từ (STOPCHARS) — cần regex.V1 để hiểu '--'
        self.RE_LOC = re.compile(rf"[\p{{Han}}--[{STOPCHARS}]]{{1,3}}[{LOC_SUFFIX}]", flags=re.V1)
        self.RE_ORG = re.compile(rf"[\p{{Han}}--[{STOPCHARS}]]{{1,4}}[{ORG_SUFFIX}]", flags=re.V1)
        self.RE_TITLE_SUF = re.compile(r"\p{Han}{1,4}[使尉]")
        self.RE_HUI = re.compile(r"諱(\p{Han}{1,3})")                 # 諱鐵木真
        self.RE_XING = re.compile(r"姓(\p{Han}{1,3})氏")             # 姓奇渥溫氏
        # gazetteer patterns (longest-first)
        self._gaz_person = self._alt(self.persons)
        self._gaz_title  = self._alt(self.titles)

    @staticmethod
    def _alt(words):
        words = sorted(set(words), key=len, reverse=True)
        if not words:
            return None
        return re.compile("|".join(re.escape(w) for w in words))

    def tag(self, sent: str) -> list[dict]:
        cands: list[tuple] = []   # (start, end, label, priority)

        def add(m, label, pri, g=0):
            cands.append((m.start(g), m.end(g), label, pri))

        # TME (priority 4) — sau đó ghép các TME liền kề
        tme_spans = [(m.start(), m.end()) for m in self.RE_TME.finditer(sent)]
        for s, e in self._merge_adjacent(tme_spans):
            cands.append((s, e, "TME", 4))
        # gazetteer PER / TITLE (priority 5 — tri thức chắc)
        if self._gaz_person:
            for m in self._gaz_person.finditer(sent):
                add(m, "PER", 5)
        if self._gaz_title:
            for m in self._gaz_title.finditer(sent):
                add(m, "TITLE", 5)
        # PER theo mẫu 諱X / 姓X氏 (priority 4)
        for m in self.RE_HUI.finditer(sent):
            cands.append((m.start(1), m.end(1), "PER", 4))
        for m in self.RE_XING.finditer(sent):
            cands.append((m.start(1), m.end(1), "PER", 4))
        # ORG / LOC hậu tố (priority 3)
        for m in self.RE_ORG.finditer(sent):
            add(m, "ORG", 3)
        for m in self.RE_LOC.finditer(sent):
            add(m, "LOC", 3)
        # TITLE hậu tố 使/尉 (priority 2)
        for m in self.RE_TITLE_SUF.finditer(sent):
            add(m, "TITLE", 2)
        # NUM (priority 1)
        for m in self.RE_NUM.finditer(sent):
            if m.group().strip():
                add(m, "NUM", 1)

        return self._resolve(sent, cands)

    @staticmethod
    def _merge_adjacent(spans):
        if not spans:
            return []
        spans = sorted(spans)
        merged = [list(spans[0])]
        for s, e in spans[1:]:
            if s <= merged[-1][1]:              # chồng hoặc liền kề
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return [(s, e) for s, e in merged]

    @staticmethod
    def _resolve(sent, cands) -> list[dict]:
        # chọn tham lam: ưu tiên priority cao, rồi span dài, không chồng lấn
        cands.sort(key=lambda c: (-c[3], -(c[1] - c[0]), c[0]))
        taken = [False] * (len(sent) + 1)
        out = []
        for s, e, label, _ in cands:
            if any(taken[s:e]):
                continue
            for i in range(s, e):
                taken[i] = True
            out.append({"text": sent[s:e], "label": label, "start": s, "end": e})
        out.sort(key=lambda x: x["start"])
        return out


# --------------------------------------------------------------------------- #
# [B] ModelNER — BERT + OpenCC
# --------------------------------------------------------------------------- #
# tagset của model → bộ nhãn đề bài
TAGMAP_CLUENER = {
    "name": "PER", "position": "TITLE",
    "organization": "ORG", "company": "ORG", "government": "ORG",
    "address": "LOC", "scene": "LOC",
    # book / game / movie → bỏ (None)
}
TAGMAP_ONTONOTES = {   # cho ckiplab (OntoNotes)
    "PERSON": "PER", "LOC": "LOC", "GPE": "LOC", "FAC": "LOC",
    "ORG": "ORG", "NORP": "ORG",
    "DATE": "TME", "TIME": "TME",
    "CARDINAL": "NUM", "QUANTITY": "NUM", "ORDINAL": "NUM",
    "MONEY": "NUM", "PERCENT": "NUM",
}

MODEL_REGISTRY = {
    "cluener": {                                  # MẶC ĐỊNH — giản thể → cần OpenCC
        "name": "uer/roberta-base-finetuned-cluener2020-chinese",
        "tagmap": TAGMAP_CLUENER, "opencc": True, "ckip": False,
    },
    "ckip": {                                     # phồn thể → KHÔNG cần OpenCC
        "name": "ckiplab/bert-base-chinese-ner",
        "tagmap": TAGMAP_ONTONOTES, "opencc": False, "ckip": True,
    },
}


class ModelNER:
    def __init__(self, key: str = "cluener"):
        cfg = MODEL_REGISTRY[key]
        self.key = key
        self.tagmap = cfg["tagmap"]
        self.use_opencc = cfg["opencc"]
        from transformers import pipeline
        if cfg["ckip"]:
            from transformers import BertTokenizerFast, AutoModelForTokenClassification
            tok = BertTokenizerFast.from_pretrained("bert-base-chinese")
            mdl = AutoModelForTokenClassification.from_pretrained(cfg["name"])
            self.nlp = pipeline("token-classification", model=mdl, tokenizer=tok,
                                aggregation_strategy="simple")
        else:
            self.nlp = pipeline("token-classification", model=cfg["name"],
                                aggregation_strategy="simple")
        if self.use_opencc:
            import opencc
            self._t2s = opencc.OpenCC("t2s")

    def _to_simplified_aligned(self, trad: str) -> str:
        """繁→简 THEO TỪNG KÝ TỰ để giữ căn lề 1-1 (map offset ngược chuẩn)."""
        out = []
        for c in trad:
            s = self._t2s.convert(c)
            out.append(s if len(s) == 1 else c)   # nếu đổi ra !=1 ký tự thì giữ nguyên
        return "".join(out)

    def _map(self, sent: str, raw) -> list[dict]:
        out = []
        for e in raw:
            label = self.tagmap.get(e["entity_group"])
            if label is None:
                continue
            s, t = e["start"], e["end"]
            if s is None or t is None:
                continue
            out.append({"text": sent[s:t], "label": label,   # lấy span trên PHỒN THỂ gốc
                        "start": s, "end": t})
        out.sort(key=lambda x: x["start"])
        return out

    def tag(self, sent: str) -> list[dict]:
        text = self._to_simplified_aligned(sent) if self.use_opencc else sent
        return self._map(sent, self.nlp(text))

    def tag_many(self, sents: list[str], batch_size: int = 32) -> list[list[dict]]:
        """Chạy theo lô cho nhanh; offset vẫn tính trên câu PHỒN THỂ gốc."""
        texts = [self._to_simplified_aligned(s) if self.use_opencc else s for s in sents]
        raws = self.nlp(texts, batch_size=batch_size)
        if sents and isinstance(raws, dict):        # phòng khi 1 câu trả dict
            raws = [raws]
        return [self._map(sent, raw) for sent, raw in zip(sents, raws)]


# --------------------------------------------------------------------------- #
def entities_public(ents: list[dict]) -> list[dict]:
    """Chỉ giữ {text,label} cho _ner.json."""
    return [{"text": e["text"], "label": e["label"]} for e in ents]


if __name__ == "__main__":
    import sys, time
    sys.stdout.reconfigure(encoding="utf-8")
    GAZ = Path(__file__).resolve().parents[1] / "gazetteer"
    tests = [
        "太祖法天啟運聖武皇帝，諱鐵木真，姓奇渥溫氏，蒙古部人。",
        "唐僖宗乾符四年，黃巢起曹濮，以溫為東南面行營先鋒使，攻陷同州。",
        "二年庚寅春正月，帝與拖雷獵于斡難河，斬首二萬餘級。",
    ]
    print("===== [A] RuleNER (gazetteer + regex) =====")
    rule = RuleNER(GAZ)
    for s in tests:
        print("·", s)
        for e in rule.tag(s):
            print(f"    {e['label']:6s} {e['text']}")
