# KẾ HOẠCH ĐỒ ÁN HCH — Ngữ liệu đơn ngữ chữ Hán, lịch sử Trung Quốc phong kiến

> Đồ án NLP giữa kỳ. Mã đồ án: **HCH**.
> Cập nhật: 2026-06-26

---

## 1. Định nghĩa bài toán

**Mục tiêu:** Xây dựng **ngữ liệu đơn ngữ chữ Hán** (monolingual corpus) chuyên ngành
**lịch sử Trung Quốc phong kiến**, đã được **tách câu** và **gán nhãn thực thể (NER)**.

**Đầu vào thực tế:** Đề cho 2 nhánh — *Ảnh* (OCR + tách câu) hoặc *Text* (tách câu + NER).
Vì đã có sẵn text số hoá (8 bộ chính sử `.txt`), đồ án rơi vào **nhánh Text**:

> **Chỉ cần: Tách câu + NER. KHÔNG cần làm OCR/hiệu đính ảnh.**

**Đặc thù quan trọng nhất:** dữ liệu là **văn ngôn / cổ văn (文言文)**, **phồn thể**,
**không phải tiếng Trung hiện đại** → quyết định toàn bộ cách chọn công cụ.

### Dữ liệu hiện có (`data/`)

Nguồn Wikisource (维基文库), **đã có sẵn dấu câu** (`。，：「」；`):

| Mã đề xuất | Bộ sử | Ký tự | Chữ Hán | Số quyển |
|---|---|---|---|---|
| HCH_001 | 春秋左氏傳 (Tả Truyện) | 381K | 300K | (chia theo 公) |
| HCH_002 | 晉書 | 1.43M | 1.15M | 130 |
| HCH_003 | 魏書 | 1.29M | 1.02M | 130 |
| HCH_004 | 新唐書 | 2.17M | 1.73M | 248 |
| HCH_005 | 新五代史 | 384K | 309K | 74 |
| HCH_006 | 元史 | 2.03M | 1.61M | 210 |
| HCH_007 | 新元史 | 1.98M | 1.62M | 257 |
| HCH_008 | 清史稿 | 5.27M | 4.34M | 529 |

Tổng ~**14 triệu chữ Hán, ~1.500 quyển** → không thể gán nhãn tay toàn bộ.

### Sản phẩm bắt buộc (OutputRequirement mục E ≈ HVH)

- `[matacpham_chapter]_seg.tsv` — tách câu, format `sentence_id \t sentence`
- `[matacpham_chapter]_ner.json` — NER, bộ nhãn tối thiểu **PER, LOC, ORG, TITLE, TME, NUM**
- Mỗi quyển một thư mục riêng, tiền tố `HCH_00X_0YY`
- (Tùy chọn) README

`sentence_id` dạng `HCH_008_012_000001` (book_chapter_running-number), khớp ví dụ
trong đề (`HVH_001_000001`).

---

## 2. Các bài toán con & thách thức

1. **Làm sạch (cleaning)** — bắt buộc, dữ liệu có nhiều "noise" Wikisource cần loại:
   - Metadata: `姊妹计划 : 数据项`, `重定向到：`, `Public domain ... false false`,
     dòng tuyên bố public domain.
   - Cước chú / 校勘記 đánh dấu `↑ ...` và tham chiếu `[ 1 ]`.
   - **Chú thích biên tập nhúng trong ngoặc `〈 … 〉`** — là chú giải của người biên tập,
     KHÔNG phải chính văn lịch sử → nên tách/loại bỏ để corpus sạch.
   - Tiêu đề cấu trúc `# 卷XX`, `## 公`, marker `經`/`傳` (riêng Tả Truyện) →
     dùng để chia quyển, không phải câu.

2. **Tách câu (segmentation)** — *thuận lợi* vì text đã có dấu câu. Chủ yếu cắt theo
   `。！？`, xử lý đúng `「」` (thoại), `；`, và phần `〈〉`. Không phải bài toán 断句 khó.

3. **NER trên văn ngôn — phần khó nhất & là trọng tâm chấm điểm:**
   - PER 人名 (朱溫, 李克用), LOC 地名 (汴州, 鳳翔), ORG 機構/軍號 (宣武軍, 崇政院),
     TITLE 官職/爵號 (節度使, 平章事, 東平王), TME 時間 (乾符四年, 春正月, 三月庚子),
     NUM 數量.
   - ⚠️ **Công cụ tiếng Trung hiện đại (jieba, HanLP mặc định, CKIP) gán nhãn rất kém
     trên 文言文.** Phải dùng công cụ chuyên cổ văn.

4. **Định dạng output + Đánh giá chất lượng** — tạo *gold set* ~300–500 câu gán tay
   để đo Precision/Recall/F1, báo cáo trong report.

---

## 3. Hướng tiếp cận đã chốt

- **NER:** dùng **mô hình mở chạy local** (không dùng LLM API).
- **Phạm vi:** **tập đại diện** (không chạy NER toàn bộ 14M chữ).

### A. Chốt phạm vi "tập đại diện"

| Hạng mục | Phạm vi | Lý do |
|---|---|---|
| **Tách câu** | **Toàn bộ 8 bộ** | Rule-based, rẻ & nhanh → corpus `_seg.tsv` đầy đủ |
| **NER** | **3 bộ đại diện 3 thời kỳ văn phong:** 春秋左氏傳 (tiên Tần) · 新五代史 (Ngũ Đại) · 清史稿 (Thanh) | Chứng minh pipeline bền với nhiều "độ khó" văn ngôn |
| | • NER **full** trên 新五代史 (~309K chữ) | Có 1 bộ hoàn chỉnh để giao |
| | • NER **N quyển mẫu** (vd 10–20 quyển) ở 2 bộ còn lại | Đủ minh chứng, kiểm soát công sức |
| **Gold set** | **300–500 câu** gán tay, trải đều 3 bộ | Vừa để **đánh giá** vừa để **fine-tune** |

### B. Công cụ (local, miễn phí)

| Bước | Công cụ | Vai trò |
|---|---|---|
| Cleaning | Python + `regex` | Loại noise Wikisource (tự viết, deterministic) |
| Tách câu | **Rule-based** (cắt `。！？；` + xử lý `「」〈〉`); hoặc **Jiayan (甲言)** | Text đã có dấu câu → rule-based đủ chính xác |
| NER baseline (không cần train) | **Jiayan NER** (HMM) + **gazetteer** | Có ngay kết quả để so sánh |
| NER chính (chất lượng cao) | **GuwenBERT** / **SikuBERT·SikuRoBERTa** / **bert-ancient-chinese** → **fine-tune** token-classification | Encoder pretrain trên 四库全書/古籍, tốt nhất cho 文言文 |
| Token/POS hỗ trợ | **UD_Classical_Chinese** (Koichi Yasuoka, HuggingFace/UDPipe/SuPar) | Tách từ + POS cổ văn, hỗ trợ ranh giới thực thể |
| Dữ liệu train/eval có sẵn | **GuNER2023**, **C-CLUE**, **二十四史 NER** | Lấy dữ liệu gán nhãn để fine-tune & đối chiếu |
| Gazetteer | **CBDB** (China Biographical Database) + tự rút từ điển từ corpus | Tăng recall & nhất quán |
| Đánh giá | `seqeval` (P/R/F1) | Báo cáo định lượng |
| Đóng gói | `pandas` + `openpyxl`, `json` | Xuất `.tsv`/`.json` |

> ⚠️ **Lưu ý kỹ thuật quan trọng:** text là **phồn thể (繁體)**, nhiều mô hình (SikuBERT,
> vài GuwenBERT) train trên **giản thể**. Cần dùng **OpenCC** chuyển 繁→简 trước khi infer,
> rồi map nhãn ngược về văn bản gốc phồn thể.

### C. Bộ nhãn & bảng ánh xạ

Bộ nhãn tối thiểu: **PER, LOC, ORG, TITLE, TME, NUM** (có thể thêm `DYNASTY`).
Các dataset cổ văn dùng tagset khác → cần bảng map:

| Nhãn đề bài | Định nghĩa cho cổ văn | Ví dụ | Map từ tagset GuNER/C-CLUE |
|---|---|---|---|
| **PER** | Nhân danh | 朱溫, 李克用, 黃巢 | NR / PER / 人名 |
| **LOC** | Địa danh | 汴州, 鳳翔, 太原, 河中 | NS / LOC / 地名 |
| **ORG** | Cơ quan, quân hiệu, phủ/viện | 宣武軍, 崇政院, 門下省 | 机构/军号 |
| **TITLE** | Quan chức, tước, phong hiệu | 節度使, 平章事, 東平王 | NO / 官职 |
| **TME** | Niên hiệu + can chi + mùa/tháng | 乾符四年, 春正月, 三月庚子 | T / 时间 |
| **NUM** | Số lượng | 三十六柵, 二萬餘級 | 数量 |

Viết **guideline gán nhãn rõ ràng** (xử lý ranh giới như `三月庚子` là 1 hay 2 TME;
`節度使` có gộp tên không…) trước khi gán gold set — đây là phần ăn điểm.

---

## 4. Quy trình triển khai (checklist)

1. **Clean** mỗi bộ → tách chính văn khỏi noise; quyết định loại bỏ chú `〈…〉`,
   cước chú `↑`, `[n]`, metadata. Chia theo `# 卷` (riêng Tả Truyện chia theo `## 公`).
2. **Segment** → sinh `_seg.tsv`, gán `sentence_id = HCH_00X_0YY_NNNNNN`.
3. **Gold set**: rút ngẫu nhiên 300–500 câu, gán tay theo guideline (2 người gán →
   đo **IAA / Cohen's κ** nếu nhóm có ≥2 người).
4. **NER**: (a) chạy **Jiayan baseline**; (b) **fine-tune GuwenBERT** trên GuNER2023+gold,
   infer (nhớ OpenCC); (c) áp **gazetteer** + map nhãn.
5. **Hậu xử lý** → xuất `_ner.json` đúng schema (`sentence_id`, `sentence`,
   `entities[{text,label}]`).
6. **Đánh giá**: `seqeval` P/R/F1 trên gold; bảng so sánh **baseline vs fine-tuned**.
7. **Đóng gói**: cây thư mục + **README** (nguồn dữ liệu, quy trình, guideline, kết quả
   eval) + report.

---

## 5. Cấu trúc thư mục & đặt tên (theo OutputRequirement)

```
HCH_005/                      # 新五代史
├── HCH_005_01/
│   ├── HCH_005_01_seg.tsv
│   └── HCH_005_01_ner.json
├── HCH_005_02/
│   ├── HCH_005_02_seg.tsv
│   └── HCH_005_02_ner.json
└── README.md
```

Mã đề xuất: `HCH_001`=春秋左氏傳, `002`=晉書, `003`=魏書, `004`=新唐書,
**`005`=新五代史**, `006`=元史, `007`=新元史, **`008`=清史稿** (xếp gần theo niên đại).

### Định dạng file

`_seg.tsv`:
```
HCH_005_01_000001	太祖神武元聖孝皇帝，姓朱氏，宋州碭山午溝里人也。
HCH_005_01_000002	唐僖宗乾符四年，黃巢起曹、濮，存、溫亡入賊中。
```

`_ner.json`:
```json
[
  {
    "sentence_id": "HCH_005_01_000002",
    "sentence": "唐僖宗乾符四年，黃巢起曹、濮，存、溫亡入賊中。",
    "entities": [
      { "text": "唐僖宗", "label": "PER" },
      { "text": "乾符四年", "label": "TME" },
      { "text": "黃巢", "label": "PER" },
      { "text": "曹", "label": "LOC" },
      { "text": "濮", "label": "LOC" }
    ]
  }
]
```

---

## 6. Rủi ro & lưu ý

- **Công cụ tiếng Trung hiện đại (jieba/HanLP/CKIP) fail trên 文言文** → bắt buộc dùng
  công cụ cổ văn.
- **Phồn↔giản** (OpenCC) như đã nêu.
- **Ranh giới TME** (niên hiệu+can chi) và **TITLE+PER** dễ sai → chốt trong guideline.
- **Nhất quán nhãn** giữa các quyển → gazetteer + hậu kiểm.
- Phân biệt **chính văn vs chú giải biên tập** (`〈〉`) — nên loại khỏi corpus lịch sử.

---

## 7. "Ăn điểm" — tiêu chí chấm

Output đúng format ✓ · pipeline tái lập được ✓ · **đánh giá định lượng (F1)** ✓ ·
**có baseline so sánh** ✓ · guideline + README rõ ràng ✓ · xử lý đúng đặc thù 文言文
(繁简, chú giải, ngày can chi) ✓.

---

## 8. Việc có thể nhờ hỗ trợ tiếp

- Viết **guideline gán nhãn + JSON schema** chi tiết.
- Dựng **script cleaning + tách câu** chạy thẳng trên `data/`.
- Soạn **notebook fine-tune GuwenBERT** cho NER.
