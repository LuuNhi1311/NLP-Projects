
---
## Đánh giá bổ sung: model FINE-TUNE (GuwenBERT trên C-CLUE)
> Model fine-tune trên **C-CLUE** (二十四史, cùng miền) — sinh **PER/LOC/ORG/TITLE**. TME/NUM lấy từ rule (bản **Hybrid+FT** ghép đủ 6 nhãn).

### seqeval trên gold 7 câu
| Phương pháp | micro-P | micro-R | micro-F1 | PER F1 | LOC F1 |
|---|---|---|---|---|---|
| Hybrid (Ⓓ+Ⓐ) | 0.750 | 0.800 | **0.774** | 0.800 | 1.000 |
| Fine-tune (C-CLUE) | 0.750 | 0.600 | **0.667** | 0.750 | 0.857 |
| Hybrid+FT | 0.688 | 0.733 | **0.710** | 0.750 | 0.857 |

### Coverage toàn tập (597 câu)
| Phương pháp | tổng | PER | LOC | ORG | TITLE | TME | NUM |
|---|---|---|---|---|---|---|---|
| Hybrid (Ⓓ+Ⓐ) | 2087 | 835 | 740 | 47 | 122 | 168 | 175 |
| Fine-tune (C-CLUE) | 1832 | 917 | 498 | 255 | 162 | 0 | 0 |
| Hybrid+FT | 2175 | 917 | 498 | 255 | 162 | 168 | 175 |
