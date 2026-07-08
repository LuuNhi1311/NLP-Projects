# Thực nghiệm tập sample — Tách câu & NER cho văn ngôn 文言文

Thư mục này là phần **thực nghiệm (proof-of-concept)** cho đồ án HCH: chạy thử
**tách câu** và **NER** trên một tập sample nhỏ (2 chương), có **benchmark so sánh
phương pháp** để nhóm họp và **chốt phương pháp** cho bản final.

> Mục tiêu (theo yêu cầu nhóm): *không nhắm độ chính xác tuyệt đối*, mà minh hoạ
> **cách áp dụng công cụ** + có số liệu so sánh. Mỗi tác vụ chạy **2 phương pháp**.

Tập sample mặc định: **元史 (HCH_006), 卷001 (太祖本紀) + 卷002 (太宗·定宗本紀)** —
文言文, phồn thể, giàu PER/LOC/TME (kể cả tên Mông Cổ phiên âm → thử thách tốt).

---

## 1. Cài đặt

```bash
pip install -r requirements.txt
# lần chạy đầu sẽ tự tải: Stanza model 'lzh' (~vài chục MB) + BERT NER (~400MB)
```

Chỉ cần **CPU** (không cần GPU) cho tập sample. Windows: chạy với UTF-8:
```bash
set PYTHONUTF8=1        # hoặc PowerShell: $env:PYTHONUTF8=1
```

## 2. Chạy

```bash
cd src
python run_pipeline.py                          # 元史 卷001, 卷002
python run_pipeline.py --book 魏書_full.txt --chapters 1 2 3
python run_pipeline.py --no-model               # bỏ Method B (khi offline)
python run_pipeline.py --no-stanza              # bỏ Stanza, chỉ rule-based
```

Kết quả ghi vào `output/HCH_006/`. Xem **`output/HCH_006/BENCHMARK_REPORT.md`**
để có bảng so sánh + khuyến nghị.

## 3. Pipeline & công cụ

```
[.txt thô] → (1) clean.py → (2) segment.py → _seg.tsv
                                    ↓
                            (3) ner.py → _ner.json → (4) benchmark.py → REPORT
```

| Bước | File | Công cụ | Ghi chú |
|---|---|---|---|
| 1. Cleaning | `clean.py` | Python + `regex` | Tách chương theo `# 卷`; loại `姊妹计划`, `↑` cước chú, `[n]`, public domain; tách chú biên tập `〈…〉` (lưu riêng, không xoá mất) |
| 2. Tách câu | `segment.py` | **[A]** rule-based (regex) · **[B]** Stanza `lzh` | [A] cắt `。！？`, nhận biết ngoặc thoại `「」` |
| 3. NER | `ner.py` | **[A]** gazetteer + regex · **[B]** BERT `cluener` + OpenCC | [B] chuyển 繁→简 giữ căn lề 1-1 rồi map nhãn về phồn thể |
| 4. Benchmark | `benchmark.py` | thống kê + đồng thuận + `seqeval` | so sánh phương pháp-với-phương pháp |

Bộ nhãn NER: **PER, LOC, ORG, TITLE, TME, NUM** (theo đề).

## 4. Định dạng output (đúng OutputRequirement)

`_seg.tsv` — `sentence_id \t sentence`, id dạng `HCH_006_001_000001`:
```
HCH_006_001_000001	太祖法天啟運聖武皇帝，諱鐵木真，姓奇渥溫氏，蒙古部人。
```

`_ner.json` — mảng record:
```json
[
  {
    "sentence_id": "HCH_006_001_000002",
    "sentence": "其十世祖孛端叉兒，母曰阿蘭果火，嫁脫奔咩哩犍，生二子…",
    "entities": [ { "text": "孛端叉兒", "label": "PER" } ]
  }
]
```

## 5. Cây thư mục

```
experiment/
├── README.md                ← file này
├── requirements.txt
├── src/
│   ├── clean.py             ← cleaning
│   ├── segment.py           ← tách câu (2 pp)
│   ├── ner.py               ← NER (2 pp)
│   ├── benchmark.py         ← hàm đo
│   └── run_pipeline.py      ← chạy tất cả (entry point)
├── gazetteer/               ← từ điển cho NER Method A (mở rộng được)
│   ├── person.txt  title.txt  nianhao.txt
└── output/HCH_006/
    ├── HCH_006_001/  HCH_006_002/   ← file _seg.tsv, _ner.json… mỗi chương
    ├── BENCHMARK_REPORT.md
    └── benchmark_seg.csv  benchmark_ner.csv
```

## 6. Mỗi thành viên nghiên cứu ≥1 phương pháp — bản đồ đóng góp

| Tác vụ | Phương pháp | File để đọc/mở rộng |
|---|---|---|
| Tách câu | Rule-based | `segment.py::segment_rule` |
| Tách câu | Stanza lzh | `segment.py::segment_stanza` |
| NER | Gazetteer + regex | `ner.py::RuleNER` + `gazetteer/*` |
| NER | BERT + OpenCC | `ner.py::ModelNER` (đổi `MODEL_REGISTRY` để thử model khác) |

Xem khuyến nghị chốt phương pháp ở cuối `BENCHMARK_REPORT.md`.
