# TÀI LIỆU HỌP TEAM — Đồ án HCH (Ngữ liệu chữ Hán, lịch sử TQ phong kiến)

> Mục đích buổi họp: **thống nhất phạm vi, hướng tiếp cận, resource, timeline và phân công.**
> Tài liệu nền: [KE_HOACH_HCH.md](KE_HOACH_HCH.md)
> Cập nhật: 2026-06-26

> ⚠️ **GIẢ ĐỊNH cần xác nhận đầu buổi họp** (ảnh hưởng timeline & phân công):
> - Số thành viên: **giả định 4 người** (doc có phương án cho 3/4/5 người).
> - Deadline nộp: **gọi là ngày D** — timeline ghi theo "tuần trước D".
> - Hạ tầng: có **Google Colab/Kaggle (GPU T4 free)** hoặc GPU lab.

---

## 1. AGENDA (đề xuất 60–90 phút)

| # | Nội dung | Thời lượng | Kết quả cần đạt |
|---|---|---|---|
| 1 | Recap mục tiêu & output bắt buộc | 5' | Cả team hiểu đề HCH |
| 2 | Hiện trạng dữ liệu & quyết định phạm vi | 15' | Chốt bộ nào vào scope NER |
| 3 | Hướng tiếp cận & các điểm cần chốt | 20' | Chốt công cụ NER, tách câu, bộ nhãn |
| 4 | Resource cần chuẩn bị | 10' | Phân ai lo môi trường/dữ liệu |
| 5 | Timeline & mốc nộp | 10' | Chốt các milestone |
| 6 | Phân chia công việc | 15' | Mỗi người có owner rõ ràng |
| 7 | Rủi ro & chốt quyết định | 10' | Điền Decision Log |

---

## 2. DỮ LIỆU — hiện trạng & điểm cần chốt

**Đã có:** 8 bộ chính sử văn ngôn (文言文), phồn thể, nguồn Wikisource, **đã có sẵn dấu câu**.
Tổng ~14M chữ Hán, ~1.500 quyển.

| Mã | Bộ sử | Chữ Hán | Quyển | Thời kỳ |
|---|---|---|---|---|
| HCH_001 | 春秋左氏傳 | 300K | theo 公 | Tiên Tần (cổ nhất) |
| HCH_002 | 晉書 | 1.15M | 130 | Tấn |
| HCH_003 | 魏書 | 1.02M | 130 | Bắc Ngụy |
| HCH_004 | 新唐書 | 1.73M | 248 | Đường |
| HCH_005 | 新五代史 | 309K | 74 | Ngũ Đại |
| HCH_006 | 元史 | 1.61M | 210 | Nguyên |
| HCH_007 | 新元史 | 1.62M | 257 | Nguyên |
| HCH_008 | 清史稿 | 4.34M | 529 | Thanh (gần nhất) |

**Điểm cần team chốt:**
- [ ] **Scope NER** = 3 bộ đại diện (春秋左氏傳 + 新五代史 + 清史稿)? Hay khác?
- [ ] **Xử lý chú giải biên tập `〈…〉`**: loại bỏ hẳn (khuyến nghị) hay giữ thành trường riêng?
- [ ] **Giữ phồn thể** ở output, chỉ dùng giản thể nội bộ khi infer (qua OpenCC)? (khuyến nghị)
- [ ] Có cần **bổ sung nguồn** khác không (đề cho phép), hay 8 bộ này là đủ?

---

## 3. HƯỚNG TIẾP CẬN — pipeline & các phương án cần bỏ phiếu

```
[8 bộ .txt thô] → (1)Clean → (2)Tách câu → _seg.tsv
                                    ↓
                            (3)NER local → _ner.json → (4)Đánh giá F1 → Report
```

**Bảng quyết định (để team bỏ phiếu):**

| Quyết định | Phương án A (khuyến nghị) | Phương án B | Đánh đổi |
|---|---|---|---|
| **Engine NER** | GuwenBERT/SikuBERT fine-tune (local) | Jiayan HMM (không train) | A chất lượng cao hơn nhưng cần GPU + dữ liệu train; B nhanh, nên dùng làm **baseline** |
| **Tách câu** | Rule-based theo dấu câu | Jiayan 断句 | A đơn giản/đủ chính xác vì đã có dấu câu |
| **Bộ nhãn** | PER, LOC, ORG, TITLE, TME, NUM | +DYNASTY (như ví dụ HVQ) | Thêm nhãn = thêm công gán & chỉnh guideline |
| **Dữ liệu train** | GuNER2023 / C-CLUE + gold tự gán | Chỉ gold tự gán | A tận dụng dữ liệu sẵn, ít công gán tay hơn |
| **繁/简** | OpenCC 繁→简 khi infer, map nhãn về phồn thể | Giữ nguyên phồn thể | Bỏ qua OpenCC → tụt độ chính xác model |

> **Khuyến nghị chốt:** A cho tất cả. Jiayan giữ làm baseline trong report (bảng so sánh).

---

## 4. RESOURCE CẦN CHUẨN BỊ

### Hạ tầng tính toán
- **GPU:** chỉ cần T4 free (Colab/Kaggle). Fine-tune GuwenBERT-base (~110M) trên vài nghìn câu
  chỉ mất ~vài chục phút. Infer tập đại diện cũng nhẹ → **không cần hạ tầng trả phí.**
- RAM ~8–16GB cho xử lý text.

### Mô hình & dữ liệu cần tải
| Loại | Tên | Nguồn |
|---|---|---|
| Encoder cổ văn | `ethanyt/guwenbert-base` | HuggingFace |
| Encoder cổ văn | `SIKU-BERT/sikubert`, `sikuroberta` | HuggingFace |
| Encoder cổ văn | `Jihuai/bert-ancient-chinese` | HuggingFace |
| Token/POS | UD_Classical_Chinese (KoichiYasuoka) | HuggingFace |
| Dataset NER | **GuNER2023**, **C-CLUE**, 二十四史 NER | GitHub |
| Gazetteer | **CBDB** (nhân danh/địa danh/quan chức) | cbdb.fas.harvard.edu |

### Phần mềm / môi trường
- Python ≥3.10, `transformers`, `datasets`, `seqeval`, `jiayan`, `opencc`, `pandas`, `openpyxl`, `regex`
- **Repo git chung** + chuẩn cấu trúc thư mục + quy ước commit
- **Kho lưu chung** (Drive/git LFS) cho dữ liệu & model

### Con người
- ≥2 người gán **gold set** (để đo IAA / Cohen's κ)

---

## 5. TIMELINE (theo "tuần trước deadline D")

| Tuần | Mốc | Sản phẩm | Owner chính |
|---|---|---|---|
| **W1** | Khởi động + Cleaning + Tách câu | `_seg.tsv` cho **cả 8 bộ**; repo + env dựng xong | Data Lead |
| **W1–W2** | Guideline + Gold set | Guideline gán nhãn v1; 300–500 câu gold (2 người gán, đo κ) | Annotation Lead |
| **W2** | NER baseline + chuẩn bị train | Kết quả Jiayan baseline; dữ liệu GuNER/C-CLUE đã chuẩn hoá | NER Lead |
| **W2–W3** | Fine-tune + Infer | Model fine-tuned; `_ner.json` cho tập đại diện | NER Lead |
| **W3** | Đánh giá + hậu xử lý | Bảng P/R/F1 (baseline vs fine-tuned); gazetteer áp dụng | Eval Lead |
| **W4** | Đóng gói + Report | Thư mục chuẩn + README + báo cáo + slide | Cả team |
| **D** | **Nộp** | Toàn bộ deliverable | — |

> Buffer: chừa **2–3 ngày cuối** để rà format output (đúng `sentence_id`, schema JSON, cây thư mục).

---

## 6. PHÂN CHIA CÔNG VIỆC

### Các gói công việc (work packages)
| WP | Nội dung | Output | Ước lượng |
|---|---|---|---|
| WP1 | Cleaning + chia quyển | script clean, chính văn sạch | 2–3 ngày |
| WP2 | Tách câu + sinh `_seg.tsv` | corpus seg toàn bộ | 1–2 ngày |
| WP3 | Guideline + gán gold set | guideline, gold 300–500 câu | 4–5 ngày |
| WP4 | NER baseline (Jiayan) | kết quả baseline | 1–2 ngày |
| WP5 | Fine-tune + infer (GuwenBERT) | model + `_ner.json` | 4–5 ngày |
| WP6 | Gazetteer + hậu xử lý + map nhãn | NER nhất quán | 2–3 ngày |
| WP7 | Đánh giá (seqeval) | bảng F1, phân tích lỗi | 2 ngày |
| WP8 | Đóng gói + README + Report + Slide | bộ nộp | 3 ngày |

### Phương án phân vai

**4 người (đề xuất):**
| Người | Vai trò | Gói chính |
|---|---|---|
| P1 | **Data/Cleaning Lead** | WP1, WP2 |
| P2 | **Annotation Lead** | WP3 (+ cùng P3 gán gold) |
| P3 | **NER Lead** | WP4, WP5, WP6 |
| P4 | **Eval/Report Lead** | WP7, WP8 |

> Gold set (WP3): **P2 + P4 cùng gán** để đo IAA. NER train (WP5) nặng nhất → P3 + hỗ trợ từ P1.

**3 người:** gộp Eval/Report vào NER Lead; Data Lead kiêm đóng gói.
**5 người:** tách riêng 1 người chuyên **Gazetteer + hậu xử lý (WP6)** và 1 người chuyên **Report/Slide**.

### Chiến lược song song hoá
- WP1→WP2 (data) chạy **độc lập** với WP3 (guideline) ngay từ W1.
- Tách câu xong sớm → các bộ chia theo quyển, **NER có thể chia theo bộ** cho nhiều người chạy song song.

---

## 7. RỦI RO & DỰ PHÒNG

| Rủi ro | Ảnh hưởng | Phương án |
|---|---|---|
| Model fail trên 文言文 / quên OpenCC | F1 thấp | Bắt buộc OpenCC; có baseline Jiayan đỡ lưng |
| Gán nhãn không nhất quán giữa người | κ thấp, NER nhiễu | Guideline kỹ + họp căn chỉnh sau 50 câu đầu |
| Scope quá lớn, không kịp | Trễ deadline | Đã giới hạn "tập đại diện"; ưu tiên 新五代史 full trước |
| Noise Wikisource sót | Câu rác trong corpus | Review mẫu sau cleaning; viết test pattern |
| Ranh giới TME/TITLE khó | Lỗi hệ thống | Chốt quy tắc trong guideline + ví dụ mẫu |

---

## 8. DECISION LOG (điền trong buổi họp)

- [ ] Scope NER: ________________________
- [ ] Engine NER: ________________________
- [ ] Bộ nhãn (có DYNASTY?): ________________________
- [ ] Xử lý `〈…〉`: ________________________
- [ ] Deadline D = ____ / Mốc nộp nội bộ = ____
- [ ] Phân vai: P1=____ P2=____ P3=____ P4=____
- [ ] Hạ tầng GPU: ________________________
- [ ] Repo + kho dữ liệu chung: ________________________

---

## 9. CẦN CHUẨN BỊ TRƯỚC BUỔI HỌP

- Mỗi người đọc trước [KE_HOACH_HCH.md](KE_HOACH_HCH.md).
- Người phụ trách hạ tầng: thử tải 1 model (vd `ethanyt/guwenbert-base`) + chạy OpenCC thử.
- Xác nhận **deadline D** và **số thành viên** để khoá timeline & phân vai cụ thể.
