# BÁO CÁO BENCHMARK — Thực nghiệm tập sample

**Bộ sử:** `元史_full.txt`  |  **Chương sample:** [1, 2]
**Mục tiêu:** minh hoạ CÁCH áp dụng công cụ cho *tách câu* và *NER* trên văn ngôn 文言文
(phồn thể), có benchmark để nhóm CHỐT phương pháp. (Không nhắm độ chính xác tuyệt đối.)

## Phương pháp đưa vào so sánh
| Tác vụ | [A] | [B] |
|---|---|---|
| Tách câu | Rule-based (regex, nhận biết 「」) | Stanza `lzh` (UD_Classical_Chinese) |
| NER | Gazetteer + regex (đủ 6 nhãn) | BERT `cluener` + OpenCC 繁→简 |

## Kết quả theo chương
### HCH_006_001 (卷1)
- Sau cleaning: **131 đoạn**, **10695 ký tự**, loại noise `{'meta': 1, 'pubdomain': 2, 'footnote': 24, 'ref': 24, 'annot': 3}`, tách 3 chú 〈〉.

**Tách câu**
- [A] rule-based: **404 câu**, dài TB 26.5 ký tự, 0.002s

**NER**
- [A] gazetteer+regex: **700 thực thể** — {'PER': 182, 'TITLE': 80, 'NUM': 103, 'LOC': 220, 'TME': 81, 'ORG': 34}

### HCH_006_002 (卷2)
- Sau cleaning: **90 đoạn**, **3901 ký tự**, loại noise `{'meta': 1, 'pubdomain': 2, 'footnote': 9, 'ref': 9, 'annot': 1}`, tách 1 chú 〈〉.

**Tách câu**
- [A] rule-based: **193 câu**, dài TB 20.2 ký tự, 0.001s

**NER**
- [A] gazetteer+regex: **361 thực thể** — {'PER': 40, 'TITLE': 42, 'NUM': 72, 'TME': 87, 'LOC': 107, 'ORG': 13}

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
