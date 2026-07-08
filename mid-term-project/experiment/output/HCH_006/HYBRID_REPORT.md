# BÁO CÁO HYBRID NER (D+A) — cổ văn 文言文 (元史 卷001+002)
> **[D] `roberta-classical-chinese`** lo **PER/LOC** ⊕ **[A] gazetteer+regex** lo **TME/NUM/TITLE/ORG**. Hợp nhất span theo ưu tiên + làm sạch ranh giới model.

## (1) seqeval P/R/F1 — GOLD team (7 câu; PER/TME/LOC)
> Gold nhỏ → minh hoạ. Mục tiêu: Hybrid ≥ max(A,D) trên micro-F1.

| Công cụ | micro-P | micro-R | micro-F1 |
|---|---|---|---|
| A rule | 0.556 | 0.333 | **0.417** |
| D classical | 0.429 | 0.800 | **0.558** |
| Hybrid D+A | 0.750 | 0.800 | **0.774** |

<details><summary>A rule — chi tiết</summary>

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
</details>

<details><summary>D classical — chi tiết</summary>

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
</details>

<details><summary>Hybrid D+A — chi tiết</summary>

```
              precision    recall  f1-score   support

         LOC      1.000     1.000     1.000         4
         NUM      0.000     0.000     0.000         0
         PER      0.857     0.750     0.800         8
         TME      0.667     0.667     0.667         3

   micro avg      0.750     0.800     0.774        15
   macro avg      0.631     0.604     0.617        15
weighted avg      0.857     0.800     0.827        15

```
</details>

## (2) Kết quả trên tập sample + phân rã nguồn

### HCH_006_001 (404 câu)
- Hybrid: **1438 thực thể** — {'PER': 646, 'TITLE': 80, 'NUM': 103, 'LOC': 494, 'TME': 81, 'ORG': 34}
- Nguồn: **[A] rule = 503**, **[D] classical = 935** (D bổ sung tên ngoài từ điển)
- Gazetteer-only cũ (`_ner.json`): 700 thực thể → Hybrid thêm +738

### HCH_006_002 (193 câu)
- Hybrid: **649 thực thể** — {'PER': 189, 'TITLE': 42, 'NUM': 72, 'LOC': 246, 'TME': 87, 'ORG': 13}
- Nguồn: **[A] rule = 269**, **[D] classical = 380** (D bổ sung tên ngoài từ điển)
- Gazetteer-only cũ (`_ner.json`): 361 thực thể → Hybrid thêm +288

**Tổng 2 chương:** 2087 thực thể — {'PER': 835, 'TITLE': 122, 'NUM': 175, 'LOC': 740, 'TME': 168, 'ORG': 47}  
Nguồn: [A] rule = 772, [D] classical = 1315

## (3) Định tính — Hybrid tag gì (nguồn A/D in kèm)

**太祖法天啟運聖武皇帝，諱鐵木真，姓奇渥溫氏，蒙古部人。**

> 太祖/PER(A) · 皇帝/TITLE(A) · 鐵木真/PER(A) · 奇渥溫/PER(A)

**以耶律楚材為中書令，粘合重山為左丞相，鎮海為右丞相。**

> 耶律楚材/PER(D) · 中書令/TITLE(A) · 粘合重山/PER(D) · 左丞相/TITLE(A) · 鎮海/PER(D) · 右丞相/TITLE(A)

**三年辛卯春二月，克鳳翔，攻洛陽、河中諸城，下之。**

> 三年辛卯春二月/TME(A) · 鳳翔/LOC(D) · 洛陽/LOC(D) · 河中/LOC(D)

**命速不台等圍南京，金主遣其弟曹王訛可入質。**

> 速不台/PER(A) · 南京/LOC(D) · 金/LOC(D) · 曹/LOC(D) · 訛可/PER(D)

## Nhận xét
- **Hybrid gộp điểm mạnh:** PER/LOC lấy từ [D] (bắt tên Mông Cổ ngoài từ điển),
  TME/NUM/TITLE/ORG lấy từ [A] (span sạch, đúng ranh giới đề). Ranh giới của [D] đã
  làm sạch (cắt 諱/姓/為… đầu span; bỏ đơn-ký-tự tôn hiệu như 帝/武/天).
- **[D] bổ sung** phần lớn PER/LOC mà gazetteer-only bỏ sót → recall tăng mạnh.
- **Còn lại cần bản final:** một số PER đơn-ký-tự nhiễu của [D] và biên TITLE ghép
  tên vẫn nên chốt trong guideline; fine-tune GuwenBERT/SikuBERT trên gold 300–500 câu
  sẽ nâng thêm precision.
