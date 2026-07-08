# SO SÁNH CÔNG CỤ NER — cổ văn 文言文 (元史 卷001+002)
> Trả lời câu hỏi họp team: *công cụ nào tối ưu độ chính xác & ưu chuộng chữ Hán cổ?*

## Công cụ đưa vào so sánh
| Mã | Công cụ | Loại | Cổ văn? | OpenCC |
|---|---|---|---|---|
| A | Gazetteer + regex | luật/từ điển | — | không |
| B | BERT CLUENER | học sâu, TQ **hiện đại giản thể** | ✗ | **cần** |
| C | ckiplab BERT NER | học sâu, TQ **hiện đại phồn thể** | ✗ | không |
| D | roberta-**classical**-chinese UPOS→map | học sâu, **CỔ VĂN native** | ✓ | không |
| E | ethanyt/**guwen-ner** | học sâu, **CỔ VĂN** (chỉ dò danh từ riêng) | ✓ | không |

## (1) seqeval P/R/F1 — GOLD team (7 câu; nhãn PER/TME/LOC)
> Gold nhỏ, chỉ có PER/TME/LOC → CHỈ minh hoạ. Bản final: gold 300–500 câu, đủ 6 nhãn.
> [E] guwen-ner không phân loại nhãn nên KHÔNG đưa vào bảng này (xem mục 2 & 3).

### [A rule]
```
              precision    recall  f1-score   support

         LOC      0.000     0.000     0.000         4
         NUM      0.000     0.000     0.000         0
         PER      1.000     0.375     0.545         8
         TME      0.667     0.667     0.667         3

   micro avg      0.556     0.333     0.417        15
   macro avg      0.417     0.260     0.303        15
weighted avg      0.667     0.333     0.424        15

```

### [B cluener]
```
              precision    recall  f1-score   support

         LOC      0.750     0.750     0.750         4
         PER      0.250     0.125     0.167         8
         TME      0.000     0.000     0.000         3

   micro avg      0.500     0.267     0.348        15
   macro avg      0.333     0.292     0.306        15
weighted avg      0.333     0.267     0.289        15

```

### [C ckip]
```
              precision    recall  f1-score   support

         LOC      0.000     0.000     0.000         4
         NUM      0.000     0.000     0.000         0
         PER      0.000     0.000     0.000         8
         TME      0.000     0.000     0.000         3

   micro avg      0.000     0.000     0.000        15
   macro avg      0.000     0.000     0.000        15
weighted avg      0.000     0.000     0.000        15

```

### [D guwen-cls]
```
              precision    recall  f1-score   support

         LOC      1.000     1.000     1.000         4
         NUM      0.000     0.000     0.000         0
         PER      1.000     1.000     1.000         8
         TME      0.000     0.000     0.000         3

   micro avg      0.429     0.800     0.558        15
   macro avg      0.500     0.500     0.500        15
weighted avg      0.800     0.800     0.800        15

```

## (2) Bao phủ trên toàn tập sample (597 câu)
> Số thực thể tìm được / nhãn = **proxy cho recall** (chưa trừ sai). ‘khớp rule’ = span+nhãn trùng KHÍT baseline A.

| Công cụ | tổng | PER | LOC | ORG | TITLE | TME | NUM | khớp rule | thời gian |
|---|---|---|---|---|---|---|---|---|---|
| A rule | 1061 | 222 | 327 | 47 | 122 | 168 | 175 | — | 0.1s |
| B cluener | 1127 | 542 | 466 | 9 | 110 | 0 | 0 | 231 | 75.6s |
| C ckip | 2386 | 1031 | 719 | 85 | 0 | 390 | 161 | 88 | 72.4s |
| D guwen-cls | 2420 | 886 | 733 | 0 | 0 | 423 | 378 | 371 | 57.5s |
| E guwen-ner | 1821 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 57.8s |

## (3) Định tính — cùng câu, các công cụ tag gì

**太祖法天啟運聖武皇帝，諱鐵木真，姓奇渥溫氏，蒙古部人。**

| Công cụ | thực thể |
|---|---|
| A rule | 太祖/PER · 皇帝/TITLE · 鐵木真/PER · 奇渥溫/PER |
| B cluener | 太祖/TITLE · 法天啟/PER · 鐵木真/PER |
| C ckip | 武皇/PER · 帝/PER · 鐵木/PER · 真/PER · 奇渥溫/PER · 氏/PER · 蒙/ORG · 古/ORG |
| D guwen-cls | 天/TME · 武/PER · 諱鐵木真/PER · 奇渥溫/PER |
| E guwen-ner | — |

**以耶律楚材為中書令，粘合重山為左丞相，鎮海為右丞相。**

| Công cụ | thực thể |
|---|---|
| A rule | 中書令/TITLE · 粘合重山/LOC · 左丞相/TITLE · 鎮海/LOC · 右丞相/TITLE |
| B cluener | 耶律楚材/PER · 中書令/TITLE · 重山/PER · 左丞相/TITLE · 鎮海/PER · 右丞相/TITLE |
| C ckip | 耶律楚/PER · 材/PER · 粘合重/PER · 山/PER · 鎮/PER · 海/PER |
| D guwen-cls | 耶律楚材/PER · 粘合重山/PER · 鎮海/PER |
| E guwen-ner | 耶律楚材/ENT · 中書/ENT · 粘合重山/ENT · 鎮海/ENT |

**三年辛卯春二月，克鳳翔，攻洛陽、河中諸城，下之。**

| Công cụ | thực thể |
|---|---|
| A rule | 三年辛卯春二月/TME · 河中諸城/LOC |
| B cluener | 鳳翔/LOC · 洛陽/LOC · 河中/LOC |
| C ckip | 三年辛卯春二/TME · 月/TME · 鳳/LOC · 翔/LOC · 洛/LOC · 陽/LOC · 河/LOC · 中/LOC |
| D guwen-cls | 三/NUM · 年/TME · 辛卯/NUM · 春/TME · 二/NUM · 月/TME · 鳳翔/LOC · 洛陽/LOC · 河中/LOC |
| E guwen-ner | 鳳翔/ENT · 洛陽/ENT · 河中諸城/ENT |

**命速不台等圍南京，金主遣其弟曹王訛可入質。**

| Công cụ | thực thể |
|---|---|
| A rule | 速不台/PER · 南京/LOC |
| B cluener | 不台/PER · 南京/LOC · 訛可/PER |
| C ckip | 南/LOC · 京/LOC · 曹王/PER · 訛/PER |
| D guwen-cls | 速不台/PER · 南京/LOC · 金/LOC · 曹/LOC · 訛可/PER |
| E guwen-ner | 速不台/ENT · 南京/ENT · 金主/ENT · 曹王訛可/ENT · 質/ENT |

## Khuyến nghị chốt (để họp team)

**Kết luận: không một công cụ đơn nào tối ưu cả 6 nhãn. Chốt HỢP NHẤT (hybrid).**

1. **PER / LOC (phần khó nhất, ăn điểm nhất) → model CỔ VĂN native [D]
   `roberta-classical-chinese`.** Đây là công cụ *ưu chuộng chữ Hán cổ* nhất:
   huấn luyện thẳng trên 文言文 **phồn thể** (UD_Classical_Chinese) → **KHÔNG cần
   OpenCC**, và bắt được **tên Mông Cổ phiên âm** (拖雷, 耶律楚材, 斡難河…) mà
   model TQ hiện đại [B]/[C] bỏ sót hoặc cắt sai.
2. **TME / NUM → RULE [A].** Model cổ văn cắt *vụn* mốc thời gian ghép
   (二年庚寅春正月 → 4 mảnh); regex gộp span sạch, đúng ranh giới đề bài.
3. **TITLE / ORG → gazetteer [A] + hậu tố** (省/軍/院/使…). Model UPOS không sinh
   trực tiếp 2 nhãn này.
4. **[E] guwen-ner** dùng làm *bộ dò danh từ riêng* để **tăng recall & soát sót**
   cho [A]/[D] (nó chỉ nói "đây là danh từ riêng", không phân loại).
5. **[B] CLUENER hiện đại** → chỉ giữ làm *đối chứng “công cụ sai miền”* trong report
   (minh chứng vì sao KHÔNG dùng NLP tiếng Trung hiện đại cho cổ văn).

**Bản FINAL:** fine-tune encoder cổ văn (GuwenBERT/SikuBERT) trên gold 300–500 câu +
GuNER2023, rồi vẫn **hợp nhất TME/NUM từ luật**. [D] là baseline “ready-to-run” rất
mạnh để đối chiếu mức tăng sau fine-tune.
