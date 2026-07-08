# BÁO CÁO THỰC NGHIỆM — Tách câu & NER cổ văn 文言文
### (Tài liệu để cả team đọc & trao đổi — chốt phương pháp cho bản final)

> **Tập sample:** 元史 (HCH_006), 卷001 (太祖本紀) + 卷002 (太宗·定宗本紀) — 文言文, phồn thể.
> **Câu hỏi cần trả lời:** *tách câu & NER — công cụ/phương pháp nào tốt hơn cho chữ Hán cổ?*
> **Cập nhật:** 2026-07-06

---

## 0. Đọc nhanh (TL;DR)

| Tác vụ | Các phương pháp đã thử | Đề xuất chốt |
|---|---|---|
| **Tách câu** | ① rule-based (regex) · ② Stanza `lzh` | **① rule-based** (text đã có sẵn dấu câu 。！？) |
| **NER** | Ⓐ gazetteer+regex · Ⓑ BERT giản thể · Ⓒ BERT phồn thể · **Ⓓ model CỔ VĂN native** · Ⓔ guwen-ner · **Hybrid Ⓓ+Ⓐ** | **Hybrid Ⓓ+Ⓐ** (Ⓓ lo PER/LOC, Ⓐ lo TME/NUM/TITLE/ORG) |

**Số đo chính (seqeval P/R/F1 trên gold 7 câu — xem giới hạn ở §4):**

| NER | micro-F1 |
|---|---|
| Ⓐ rule | 0.417 |
| Ⓓ classical | 0.558 |
| **Hybrid Ⓓ+Ⓐ** | **0.774** |

> ⚠️ **Lưu ý ngay từ đầu:** con số F1 ở trên đo trên **gold chỉ 7 câu** → **chỉ mang tính minh hoạ**,
> CHƯA phải kết luận độ chính xác cuối cùng. Lý do & cách đánh giá đầy đủ ở **§4** (phần quan trọng nhất).

---

## 1. Mục tiêu thực nghiệm

Đây là bước **proof-of-concept**: chạy thử pipeline tách câu + NER trên tập sample nhỏ, để **so sánh công cụ**
và **chốt phương pháp** trước khi làm bản final trên nhiều bộ sử. **Không** nhắm độ chính xác tuyệt đối ở bước này.

Mỗi tác vụ chạy **≥2 phương pháp** để có cơ sở so sánh (đúng yêu cầu "mỗi thành viên nghiên cứu ≥1 phương pháp").

---

## 2. Dữ liệu & file đã xuất (đúng OutputRequirement)

Pipeline: `[.txt thô] → clean.py → segment.py → ner.py → benchmark`. Sau làm sạch:

| Chương | Đoạn | Ký tự | Câu (tách) |
|---|---|---|---|
| HCH_006_001 (卷1) | 131 | 10 695 | **404** |
| HCH_006_002 (卷2) | 90 | 3 901 | **193** |

**Các file sinh ra trong `output/HCH_006/HCH_006_00X/`:**

| File | Nội dung | Trạng thái |
|---|---|---|
| `..._seg.tsv` | **Tách câu (canonical)** — `sentence_id \t sentence` | ✅ theo đúng format đề |
| `..._ner.json` | **NER (canonical)** — `[{sentence_id, sentence, entities:[{text,label}]}]`, đủ 6 nhãn | ✅ theo đúng format đề |
| `..._ner.hybrid.json` | NER bằng **Hybrid Ⓓ+Ⓐ** (bản đề xuất mới) | ✅ đã xuất |
| `..._ner.model.json` | NER bằng BERT (đối chứng) | ✅ đã xuất |
| `..._seg.stanza.tsv` | Tách câu bằng Stanza (đối chứng) | ✅ đã xuất |
| `..._annotations.txt` | Chú giải biên tập `〈…〉` tách riêng (không mất) | ✅ đã xuất |

Bộ nhãn NER: **PER, LOC, ORG, TITLE, TME, NUM**. `sentence_id` dạng `HCH_006_001_000001`.

> **Trả lời câu hỏi "đã xuất file như yêu cầu chưa":** ✅ **Rồi.** File bắt buộc là `_seg.tsv` + `_ner.json`
> đã có cho cả 2 chương, đúng schema. Các file `.hybrid.json` / `.model.json` / `.stanza.tsv` là **biến thể
> phương pháp để so sánh** — team xem rồi chốt dùng bản nào làm canonical cho final.

---

## 3. Các phương pháp đưa vào so sánh

### 3.1. Tách câu
| # | Phương pháp | Ý tưởng |
|---|---|---|
| ① | **Rule-based** (regex) | Cắt tại 。！？, nhận biết ngoặc thoại 「」 (không cắt trong thoại) |
| ② | **Stanza `lzh`** | Model tokenizer/segmenter cổ văn (UD_Classical_Chinese) |

### 3.2. NER
| Mã | Công cụ | Loại | Cổ văn native? | OpenCC |
|---|---|---|---|---|
| **Ⓐ** | Gazetteer + regex | luật/từ điển (tự viết) | — | không |
| **Ⓑ** | BERT CLUENER (`uer/roberta…cluener`) | học sâu, TQ **hiện đại giản thể** | ✗ | **bắt buộc** |
| **Ⓒ** | ckiplab BERT NER | học sâu, TQ **hiện đại phồn thể** | ✗ | không |
| **Ⓓ** | `roberta-classical-chinese` UPOS→map | học sâu, **CỔ VĂN native** | ✓ | **không** |
| **Ⓔ** | `ethanyt/guwen-ner` | học sâu, **CỔ VĂN** (chỉ dò danh từ riêng) | ✓ | không |
| **Hybrid** | **Ⓓ (PER/LOC) ⊕ Ⓐ (TME/NUM/TITLE/ORG)** | hợp nhất | ✓+luật | không |

---

## 4. ⭐ CÁCH ĐÁNH GIÁ ĐỘ CHÍNH XÁC — khi CHƯA có ground truth đầy đủ

> Đây là phần trả lời trực tiếp câu hỏi của team: *"không có file ground truth thì đo độ chính xác bằng gì?"*

**Sự thật cần nói rõ:** để tính **độ chính xác thật** (Precision/Recall/F1) thì **BẮT BUỘC phải có
ground truth (gold)** — tức tập câu được **con người gán nhãn tay** làm chuẩn. Hiện tại nhóm **chưa có
gold đủ lớn** (mới chỉ có **7 câu** gán thử). Vì vậy thực nghiệm này đo bằng **4 cách**, chia làm 2 nhóm:

### 🟢 Nhóm A — CÓ chuẩn (đo được P/R/F1 thật, nhưng chuẩn còn rất nhỏ)

**(1) seqeval trên gold 7 câu** (`gold/HCH_006_gold_demo.json`, team gán tay).
- Đây là chỗ **DUY NHẤT** tính ra **Precision / Recall / F1 thật**.
- So khớp span **(vị trí + nhãn)** giữa dự đoán và gold; công thức chuẩn NER:
  `Precision = đúng / (đúng+thừa)`, `Recall = đúng / (đúng+thiếu)`, `F1 = 2PR/(P+R)`.
- **Giới hạn:** gold chỉ **7 câu / 15 thực thể / 3 nhãn (PER, TME, LOC)** → con số **chỉ minh hoạ cơ chế**,
  KHÔNG đủ để kết luận. (Ví dụ: chưa hề đánh giá được ORG/TITLE/NUM vì gold chưa có các nhãn đó.)

### 🟡 Nhóm B — KHÔNG cần chuẩn (đo GIÁN TIẾP, chỉ để SO SÁNH phương pháp với nhau)

**(2) Độ bao phủ (coverage) — đếm số thực thể mỗi công cụ tìm được / nhãn.**
- Là **proxy (đại diện) cho RECALL**: tìm được nhiều hơn ⇒ *có thể* recall cao hơn.
- ⚠️ **KHÔNG đo được Precision:** không biết trong số tìm được có bao nhiêu **sai**. Nên **"tìm nhiều hơn" ≠
  "tốt hơn"** — có thể chỉ là nhiều false-positive hơn (ví dụ Ⓒ ckip tìm 2 386 thực thể nhưng phần lớn **vỡ vụn**).

**(3) Độ đồng thuận giữa các phương pháp (inter-method agreement).**
- Trên **cùng tập câu**, đếm số span mà 2 công cụ **trùng KHÍT** (cùng start+end+nhãn).
- Ý nghĩa: 2 công cụ **độc lập** cùng đồng ý ⇒ span đó **đáng tin hơn** (kiểu "đồng thuận / silver").
  Chỗ **bất đồng** ⇒ đánh dấu để người review. Không cần gold.
- (Với tách câu: đo bằng **Jaccard** trên tập ranh giới cắt — xem `benchmark.py`.)

**(4) Định tính — con người soi trực tiếp.**
- Team đọc **vài câu tiêu biểu**, tự mắt đánh giá công cụ nào tag đúng/sai (xem §5.4).
- Đây **hiện là nguồn phán xét "ai đúng hơn" chính**, vì các số ở (2)(3) không phân định đúng/sai tuyệt đối.

### 📌 Kết luận về đánh giá (nói thẳng với team)

| Muốn biết… | Đo được chưa? | Bằng cách nào |
|---|---|---|
| Xu hướng recall (tìm được nhiều/ít) | ✅ tương đối | coverage (2) |
| Span nào đáng tin | ✅ tương đối | agreement (3) |
| Công cụ nào tag đúng ở ca cụ thể | ✅ định tính | soi tay (4) |
| **Xếp hạng độ chính xác CHÍNH THỨC (P/R/F1)** | ❌ **chưa** | **cần gold 300–500 câu** |

➡️ **Muốn trả lời dứt khoát "phương pháp của ai tốt hơn" thì phải xây GOLD SET 300–500 câu** (đây chính là
**WP3** trong kế hoạch). Máy đánh giá đã dựng sẵn (`eval_demo.py` / `bench_tools.py` chạy seqeval) — **chỉ cần
thay file gold lớn vào là ra kết quả chính thức**, không phải viết lại code.

---

## 5. Kết quả thực nghiệm

### 5.1. Tách câu
- ① rule-based: **404 câu** (卷1) / **193 câu** (卷2); nhanh (~0.002s), khớp đúng định nghĩa "câu" (kết bằng 。).
- ② Stanza `lzh`: cắt **vụn hơn ~2–3×** (ở mức cụm/mệnh đề, tách rời cả `諱|tên`) → **không khớp** format `_seg.tsv`.
- **Chốt: dùng ① rule-based.** Stanza giữ làm đối chứng / dùng cho tokenize-POS sau này nếu cần.

### 5.2. NER — seqeval trên gold 7 câu (P/R/F1 thật, nhưng minh hoạ)

| NER | micro-P | micro-R | micro-F1 | Ghi chú |
|---|---|---|---|---|
| Ⓐ rule | 0.556 | 0.333 | 0.417 | precision khá, **recall thấp** (sót tên ngoài từ điển) |
| Ⓑ cluener | 0.500 | 0.267 | 0.348 | cần OpenCC, hay sót họ (耶律…) |
| Ⓒ ckip | 0.000 | 0.000 | **0.000** | **vỡ vụn từng ký tự** — tokenizer hiện đại fail trên 文言文 |
| Ⓓ classical | 0.429 | **0.800** | 0.558 | **recall cao nhất**; PER & LOC đạt **F1=1.0**; bị TME cắt vụn kéo xuống |
| **Hybrid Ⓓ+Ⓐ** | **0.750** | **0.800** | **0.774** | **tốt nhất** — recall của Ⓓ + span sạch của Ⓐ |

### 5.3. NER — coverage & agreement trên TOÀN tập sample (597 câu, KHÔNG gold)

| Công cụ | tổng | PER | LOC | ORG | TITLE | TME | NUM | khớp-khít Ⓐ |
|---|---|---|---|---|---|---|---|---|
| Ⓐ rule | 1061 | 222 | 327 | 47 | 122 | 168 | 175 | — |
| Ⓑ cluener | 1127 | 542 | 466 | 9 | 110 | 0 | 0 | 231 |
| Ⓒ ckip | 2386 | 1031 | 719 | 85 | 0 | 390 | 161 | 88 |
| Ⓓ classical | 2420 | 886 | 733 | 0 | 0 | 423 | 378 | 371 |
| Ⓔ guwen-ner | 1821 | *(chỉ "danh từ riêng", không phân loại)* | | | | | | — |

*Đọc bảng:* Ⓑ/Ⓓ **không có TME/NUM** (cột =0) → thiếu nhãn. Ⓒ số rất lớn nhưng **chủ yếu vỡ vụn** (xem §5.4).
Ⓓ đồng thuận với Ⓐ **cao nhất (371)** → hai hướng độc lập (model cổ văn vs luật) xác nhận lẫn nhau nhiều nhất.

### 5.4. NER — định tính (đây là chỗ THẤY RÕ ai đúng/sai)

**Câu:** `以耶律楚材為中書令，粘合重山為左丞相，鎮海為右丞相。`

| Công cụ | Kết quả | Nhận xét |
|---|---|---|
| Ⓐ rule | `粘合重山/LOC · 鎮海/LOC` (sai) | nhầm vì hậu tố 山/海; **sót** 耶律楚材 (ngoài từ điển) |
| Ⓒ ckip | `耶律楚/PER·材/PER·粘合重/PER·山/PER…` | **vỡ vụn**, sai ranh giới |
| **Ⓓ classical** | `耶律楚材/PER · 粘合重山/PER · 鎮海/PER` | **đúng cả 3** tên |
| **Hybrid** | `耶律楚材/PER(Ⓓ)·中書令/TITLE(Ⓐ)·粘合重山/PER(Ⓓ)·左丞相/TITLE(Ⓐ)·鎮海/PER(Ⓓ)·右丞相/TITLE(Ⓐ)` | **đúng & đủ nhãn** |

**Câu:** `三年辛卯春二月，克鳳翔，攻洛陽、河中諸城，下之。`

| Công cụ | Kết quả | Nhận xét |
|---|---|---|
| Ⓐ rule | `三年辛卯春二月/TME` (đúng, gộp sạch) | mạnh ở TME |
| Ⓓ classical | `三/NUM·年/TME·辛卯/NUM·春/TME·二/NUM·月/TME` (**vụn**) + `鳳翔/洛陽/河中 LOC` (đúng) | mạnh LOC, yếu TME |
| **Hybrid** | `三年辛卯春二月/TME(Ⓐ) · 鳳翔/LOC(Ⓓ) · 洛陽/LOC(Ⓓ) · 河中/LOC(Ⓓ)` | lấy điểm mạnh mỗi bên |

> Đây là bằng chứng rõ nhất cho câu hỏi "ai tốt hơn": **model cổ văn Ⓓ thắng ở PER/LOC (tên Mông Cổ), luật Ⓐ
> thắng ở TME/NUM**, và **Hybrid gộp được cả hai**.

### 5.5. Hybrid Ⓓ+Ⓐ — kết quả trên tập sample
- 卷1: **1438 thực thể** (Ⓐ đóng góp 503, **Ⓓ bổ sung 935**) — so với gazetteer-only cũ (700) → **+738**.
- 卷2: **649 thực thể** (Ⓐ 269, **Ⓓ 380**) — so với cũ (361) → **+288**.
- Ⓓ bổ sung phần lớn là **PER/LOC ngoài từ điển** (tên Mông Cổ: 脫奔咩哩犍, 博寒葛答黑, 斡難河…) → **recall tăng mạnh**.
- Đã xử lý sạch ranh giới của Ⓓ: cắt tiền tố 諱/姓/為…, **tách liệt kê** `涿、易`→2 địa danh, bỏ dấu câu/校勘 `（X）`,
  loại đơn-ký-tự tôn hiệu 帝/武/天. **Kiểm tra: 0 thực thể dính dấu câu.**

---

## 6. Kết luận & khuyến nghị chốt (để bỏ phiếu)

1. **Tách câu → RULE-BASED ①.**
2. **NER → HYBRID Ⓓ+Ⓐ**: `roberta-classical-chinese` (PER/LOC) + gazetteer/regex (TME/NUM/TITLE/ORG).
   Đây là công cụ **ưu chuộng chữ Hán cổ nhất**: train thẳng trên cổ văn **phồn thể**, **không cần OpenCC**,
   bắt được **tên Mông Cổ phiên âm** mà model TQ hiện đại (Ⓑ/Ⓒ) bỏ sót/vỡ vụn.
3. **Ⓑ CLUENER / Ⓒ ckip** → chỉ giữ làm **đối chứng "công cụ sai miền"** trong report (minh chứng vì sao
   KHÔNG dùng NLP tiếng Trung hiện đại cho cổ văn).
4. **Ⓔ guwen-ner** → bộ dò danh từ riêng để **tăng recall / soát sót**.

---

## 7. Việc cần làm tiếp (bắt buộc để có kết luận độ chính xác chính thức)

1. **⭐ Xây GOLD SET 300–500 câu (WP3)** — 2 người gán tay theo guideline, đo **Cohen's κ (IAA)**.
   → Đây là điều kiện DUY NHẤT để tính được **P/R/F1 chính thức** & xếp hạng phương pháp một cách chắc chắn.
2. Chạy lại seqeval trên gold lớn (code đã sẵn, chỉ thay file).
3. Bản final: **fine-tune GuwenBERT/SikuBERT** trên gold + GuNER2023 (vẫn giữ TME/NUM từ luật); Hybrid Ⓓ+Ⓐ
   là **baseline mạnh** để đo mức cải thiện sau fine-tune.

---

## Phụ lục — Cách chạy lại thực nghiệm

```bash
cd experiment/src
python run_pipeline.py           # clean → tách câu → NER (Ⓐ gazetteer, Ⓑ BERT) → BENCHMARK_REPORT.md
python bench_tools.py            # so sánh 5 công cụ NER (Ⓐ..Ⓔ) → TOOLS_COMPARISON.md
python run_hybrid.py             # Hybrid Ⓓ+Ⓐ + seqeval → HYBRID_REPORT.md + _ner.hybrid.json
python eval_demo.py              # minh hoạ seqeval trên gold 7 câu
```

**Báo cáo chi tiết kèm theo:**
`output/HCH_006/TOOLS_COMPARISON.md` (so sánh 5 công cụ) · `output/HCH_006/HYBRID_REPORT.md` (chi tiết Hybrid).
