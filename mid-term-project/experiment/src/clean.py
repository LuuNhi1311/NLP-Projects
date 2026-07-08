# -*- coding: utf-8 -*-
"""
clean.py — Làm sạch (cleaning) ngữ liệu chữ Hán từ nguồn Wikisource.

Nhiệm vụ:
  1. Tách một bộ sử (.txt) thành từng CHƯƠNG (quyển) theo marker `# 卷XXX`.
  2. Loại bỏ NOISE của Wikisource:
       - metadata:  `姊妹计划 : 数据项`
       - tuyên bố public domain:  `...公有领域`, `Public domain ... false false`
       - cước chú cuối chương:  dòng bắt đầu bằng `↑`
       - tham chiếu cước chú trong câu:  `[ 1 ]`, `[ 12 ]`
       - chú giải biên tập nhúng:  `〈 ... 〉`  (là chú của người biên tập, KHÔNG phải chính văn)
  3. Tách phần TIÊU ĐỀ mục (vd `太祖`, `太宗 定宗`) khỏi CHÍNH VĂN.

Thiết kế deterministic (chỉ dùng regex) → tái lập 100%, không phụ thuộc model.
Chạy trực tiếp:  python clean.py
"""
from __future__ import annotations
import re
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

# --------------------------------------------------------------------------- #
# Cấu hình
# --------------------------------------------------------------------------- #
# Mã đề xuất cho mỗi bộ sử (theo KE_HOACH_HCH.md)
BOOK_CODE = {
    "Tả Truyện - 春秋左氏傳_full.txt": "HCH_001",
    "晉書_full.txt":   "HCH_002",
    "魏書_full.txt":   "HCH_003",
    "新唐書_full.txt": "HCH_004",
    "新五代史_full.txt": "HCH_005",
    "元史_full.txt":   "HCH_006",
    "新元史_full.txt": "HCH_007",
    "清史稿_full.txt": "HCH_008",
}

# Dấu câu kết thúc câu (dùng để phân biệt chính văn vs tiêu đề)
SENTENCE_PUNCT = "。！？；，、："

# Tiêu đề cấu trúc cần loại hẳn (mục cước chú, không phải nội dung lịch sử)
DROP_HEADINGS = {"校勘記", "校勘记"}

# --- các pattern noise ------------------------------------------------------ #
RE_CHAPTER   = re.compile(r"^#\s*卷\s*(\d+)")          # # 卷001
RE_SECTION   = re.compile(r"^#\s*(.+)$")               # # 進元史表 (mục không phải 卷)
RE_META      = re.compile(r"姊妹计划|数据项|重定向到")
RE_PUBDOMAIN = re.compile(r"公有领域|Public\s*domain|本.{0,6}作品.{0,4}(全世界|属于)")
RE_FOOTNOTE  = re.compile(r"^\s*↑")                    # dòng cước chú
RE_REF       = re.compile(r"\[\s*\d+\s*\]")            # [ 1 ] tham chiếu trong câu
RE_ANNOT     = re.compile(r"〈[^〈〉]*〉")               # 〈 chú biên tập 〉
RE_SPACES    = re.compile(r"[ \t　]+")             # gộp khoảng trắng (kể cả 　)


@dataclass
class Chapter:
    """Một chương (quyển) đã làm sạch."""
    book_code: str
    book_name: str
    chapter_id: str                 # vd HCH_006_001
    chapter_num: int
    headings: list[str] = field(default_factory=list)   # tiêu đề mục (太祖, 太宗...)
    paragraphs: list[str] = field(default_factory=list)  # chính văn, mỗi đoạn 1 phần tử
    removed: dict = field(default_factory=dict)          # thống kê noise đã loại
    raw_chars: int = 0
    clean_chars: int = 0
    annotations: list[str] = field(default_factory=list)  # nội dung 〈〉 đã tách (lưu lại, không mất)


def _is_heading(line: str) -> bool:
    """Tiêu đề mục = dòng NGẮN, KHÔNG chứa dấu câu (太祖, 太宗 定宗, 序紀...)."""
    stripped = line.strip()
    if not stripped:
        return False
    if any(p in stripped for p in SENTENCE_PUNCT):
        return False
    return len(stripped.replace(" ", "")) <= 8


def clean_line(line: str, stats: dict) -> str | None:
    """Làm sạch 1 dòng chính văn. Trả None nếu dòng bị loại hoàn toàn."""
    # tách & lưu chú biên tập 〈〉 (đếm rồi loại khỏi chính văn)
    annots = RE_ANNOT.findall(line)
    if annots:
        stats["annot"] += len(annots)
        stats["_annot_texts"].extend(a[1:-1].strip() for a in annots)
        line = RE_ANNOT.sub("", line)
    # loại tham chiếu cước chú [ n ]
    n_ref = len(RE_REF.findall(line))
    if n_ref:
        stats["ref"] += n_ref
        line = RE_REF.sub("", line)
    # gộp khoảng trắng
    line = RE_SPACES.sub("", line).strip()
    return line or None


def split_chapters(text: str, book_name: str, book_code: str) -> list[Chapter]:
    """Tách toàn bộ text của 1 bộ sử thành list Chapter đã làm sạch."""
    lines = text.splitlines()
    chapters: list[Chapter] = []
    cur: Chapter | None = None
    stats_template = lambda: {"meta": 0, "pubdomain": 0, "footnote": 0,
                              "ref": 0, "annot": 0, "_annot_texts": []}
    stats = stats_template()

    for line in lines:
        m = RE_CHAPTER.match(line)
        if m:                                   # gặp chương mới
            if cur is not None:
                _finalize(cur, stats)
                chapters.append(cur)
            num = int(m.group(1))
            cur = Chapter(
                book_code=book_code, book_name=book_name,
                chapter_id=f"{book_code}_{num:03d}", chapter_num=num,
            )
            stats = stats_template()
            continue

        if cur is None:                         # phần trước chương đầu (tựa sách, 進元史表) → bỏ
            continue

        cur.raw_chars += len(line)

        # --- loại noise theo dòng ---
        if RE_META.search(line):
            stats["meta"] += 1;      continue
        if RE_PUBDOMAIN.search(line):
            stats["pubdomain"] += 1; continue
        if RE_FOOTNOTE.match(line):
            stats["footnote"] += 1;  continue
        if not line.strip():
            continue

        # tiêu đề mục?
        if _is_heading(line):
            h = line.strip()
            if h not in DROP_HEADINGS:
                cur.headings.append(h)
            continue

        cleaned = clean_line(line, stats)
        if cleaned:
            cur.paragraphs.append(cleaned)

    if cur is not None:
        _finalize(cur, stats)
        chapters.append(cur)
    return chapters


def _finalize(ch: Chapter, stats: dict):
    ch.annotations = stats.pop("_annot_texts")
    ch.removed = stats
    ch.clean_chars = sum(len(p) for p in ch.paragraphs)


# --------------------------------------------------------------------------- #
# CLI / demo
# --------------------------------------------------------------------------- #
def clean_book(txt_path: Path) -> list[Chapter]:
    book_name = txt_path.name
    book_code = BOOK_CODE.get(book_name, "HCH_XXX")
    text = txt_path.read_text(encoding="utf-8")
    return split_chapters(text, book_name, book_code)


if __name__ == "__main__":
    import sys
    DATA = Path(__file__).resolve().parents[2] / "data"
    target = DATA / "元史_full.txt"
    chapters = clean_book(target)
    print(f"Bộ: {target.name}  → {len(chapters)} chương")
    for ch in chapters[:2]:
        print(f"\n=== {ch.chapter_id} (卷{ch.chapter_num}) ===")
        print(f"  headings   : {ch.headings}")
        print(f"  #đoạn      : {len(ch.paragraphs)}")
        print(f"  raw→clean  : {ch.raw_chars} → {ch.clean_chars} ký tự")
        print(f"  noise loại : {ch.removed}")
        print(f"  #chú 〈〉   : {len(ch.annotations)}  (vd: {ch.annotations[:2]})")
        print(f"  đoạn đầu   : {ch.paragraphs[0][:60]}...")
