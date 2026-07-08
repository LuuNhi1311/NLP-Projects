# Đo P/R/F1 bằng seqeval — GOLD MẪU (minh hoạ cơ chế)

> Gold **7 câu / 15 thực thể** — chỉ để demo CÁCH đo, KHÔNG phải kết luận độ chính xác. Bản final: gold 300-500 câu.

## [A] Gazetteer + regex
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

## [B] BERT (cluener) + OpenCC
```
              precision    recall  f1-score   support

         LOC      0.750     0.750     0.750         4
         PER      0.250     0.125     0.167         8
         TME      0.000     0.000     0.000         3

   micro avg      0.500     0.267     0.348        15
   macro avg      0.333     0.292     0.306        15
weighted avg      0.333     0.267     0.289        15

```

## Nhận định
- [A] chính xác cao ở PER (trong từ điển) & TME, nhưng **recall PER thấp** (sót tên ngoài gazetteer) và **LOC yếu** (hậu tố không phủ 鳳翔/洛陽).
- [B] **bắt LOC tốt**, nhưng fail PER (tên Mông Cổ) và **không có nhãn TME/NUM**.
- → Hai công cụ **bổ sung**: final nên fine-tune encoder cổ văn + hợp nhất gazetteer (TME/NUM từ luật; PER/LOC/ORG từ model).
