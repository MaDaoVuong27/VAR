# Đề bài & Quy định

# Thể thức

- Vòng 1, các thí sinh dự thi nộp kết quả dự đoán dưới dạng file JSON theo đúng format do Ban Tổ chức (BTC) quy định. File nộp bao gồm một file *output.zip* có cấu trúc sau khi giải nén như sau:

```text
output/
    ├── 1.json      # Nhãn của bản ghi 1
    ├── 2.json      # Nhãn của bản ghi 2
    ├── …
    └── 100.json
```

Chi tiết dạng json trong output sẽ được nêu ở ví dụ dưới.

- Lưu ý:
  - Trước khi vòng 1 kết thúc, BTC yêu cầu top ~15 đội gửi trước source code riêng để thực hiện dùng lại và đánh giá trên dữ liệu private test. Việc này nhằm tránh tình trạng gian lận nộp file hard code output với input được cung cấp.
  - Source code bao gồm:
    - tất cả các file code của nhóm (data processing, training, inference, ...)
    - data nhóm sử dụng
    - model weights
    - 1 file readme hướng dẫn cài đặt
  - Nếu BTC không thể cài đặt được code của nhóm thi, nhóm thi sẽ được liên lạc riêng để hỗ trợ trong 1 khoảng thời gian nhất định. Nếu nhóm không thể cung cấp hỗ trợ kịp thời sẽ bị loại.
- VD input-output vòng 1:
  - Input:

> 'Danh sách thuốc trước nhập viện chính xác và đầy đủ. 1. amlodipine 10 mg po daily 2. aspirin 81 mg po daily 3. metoprolol succinate xl 50 mg po daily 4. guaifenesin ml po q6h:prn điều trị ho 5. nystatin oral suspension 5 ml po qid:prn điều trị đau nhức 6. acetaminophen 325-650 mg po q6h:prn điều trị sốt đau 7. pravastatin 40 mg po daily 8. docusate sodium 100 mg po bid điều trị táo bón 9. senna 8.6 mg po bid:prn điều trị táo bón 10. clonazepam 0.5 mg po qam:prn điều trị lo âu 11. clonazepam 1.5 mg po qhs điều trị lo âu mất ngủ'

- Output:

```json
[
  {
    "text": "amlodipine 10 mg po daily",
    "type": "THUỐC",
    "candidates": ["308135"],
    "assertions": ["isHistorical"],
    "position": [58, 83]
  },
  {
    "text": "aspirin 81 mg po daily",
    "type": "THUỐC",
    "candidates": ["243670"],
    "assertions": ["isHistorical"],
    "position": [89, 111]
  },
  {
    "text": "metoprolol succinate xl 50 mg po daily",
    "type": "THUỐC",
    "candidates": ["866436"],
    "assertions": ["isHistorical"],
    "position": [117, 155]
  },
  {
    "text": "guaifenesin ml po q6h:prn",
    "type": "THUỐC",
    "candidates": ["392085"],
    "assertions": ["isHistorical"],
    "position": [161, 186]
  },
  {
    "text": "ho",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [196, 198]
  },
  {
    "text": "nystatin oral suspension 5 ml po qid:prn",
    "type": "THUỐC",
    "candidates": ["7597"],
    "assertions": ["isHistorical"],
    "position": [204, 244]
  },
  {
    "text": "đau nhức",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [254, 262]
  },
  {
    "text": "acetaminophen 325-650 mg po q6h:prn",
    "type": "THUỐC",
    "candidates": ["313782"],
    "assertions": ["isHistorical"],
    "position": [268, 303]
  },
  {
    "text": "sốt đau",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [313, 320]
  },
  {
    "text": "pravastatin 40 mg po daily",
    "type": "THUỐC",
    "candidates": ["904475"],
    "assertions": ["isHistorical"],
    "position": [326, 352]
  },
  {
    "text": "docusate sodium 100 mg po bid",
    "type": "THUỐC",
    "candidates": ["1099279"],
    "assertions": ["isHistorical"],
    "position": [358, 387]
  },
  {
    "text": "táo bón",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [397, 404]
  },
  {
    "text": "senna 8.6 mg po bid:prn",
    "type": "THUỐC",
    "candidates": ["312935"],
    "assertions": ["isHistorical"],
    "position": [410, 433]
  },
  {
    "text": "táo bón",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [443, 450]
  },
  {
    "text": "clonazepam 0.5 mg po qam:prn",
    "type": "THUỐC",
    "candidates": ["197527"],
    "assertions": ["isHistorical"],
    "position": [457, 485]
  },
  {
    "text": "lo âu",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [495, 500]
  },
  {
    "text": "clonazepam 1.5 mg po qhs",
    "type": "THUỐC",
    "candidates": ["197528"],
    "assertions": ["isHistorical"],
    "position": [507, 531]
  },
  {
    "text": "lo âu",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [541, 546]
  },
  {
    "text": "mất ngủ",
    "type": "TRIỆU_CHỨNG",
    "assertions": [],
    "position": [547, 554]
  }
]
```

# Metric đánh giá

Kết quả của thí sinh sẽ được tính trên tập test theo các metric sau:

- Xét theo xác định tên khái niệm: sử dụng Word Error Rate (WER) trên trường text.
- Xét theo xác định các assertions giữa khái niệm: sử dụng metric là độ tương đồng Jaccard (Jaccard similarity) với các bệnh, thuốc và triệu chứng tương ứng, lấy trung bình tất cả các giá trị này thành 1 điểm J(assertion)
- Xét theo xác định candidates trong khái niệm: sử dụng metric giống với xác định assertion
- Kết quả cuối cùng được tính điểm theo công thức:

$$
final\_score = 0.3 \cdot text\_score + 0.3 \cdot assertions\_score + 0.4 \cdot candidates\_score
$$

Trong đó, với mỗi i là 1 sample trong tập test, mỗi k là 1 candidate trong sample i, WER(i) là WER của trường text trong sample i, ground_truth(k), prediction(k) lần lượt là tập ground truth, prediction của candidate k trong sample i, J_X(i) là độ tương đồng Jaccard của sample i xét trên trường X tương ứng của output:

$$
text\_score = \frac{\sum_{i \in test}(1 - WER(i))}{len(test)}
$$

$$
assertions\_score = \frac{\sum_{i \in test}J_{assertions}(i)}{len(test)}
$$

$$
candidates\_score = \frac{\sum_{i \in test} J_{candidates}(i) \cdot \left(\sum_{k \in i} (len(ground\_truth(k)) + 1)\right)}{\sum_{i \in test}\sum_{k \in i}(len(ground\_truth(k)) + 1)}
$$

$$
J_X(i) = 1 \text{ nếu } len(ground\_truth_X(i)) = 0 \text{ và } len(prediction_X(i)) = 0
$$

$$
J_X(i) = 0 \text{ nếu } len(ground\_truth_X(i)) = 0 \text{ và } len(prediction_X(i)) \ne 0
$$

$$
J_X(i) = \frac{|ground\_truth_X(i) \cap prediction_X(i)|}{|ground\_truth_X(i) \cup prediction_X(i)|} \text{ trong các trường hợp còn lại}
$$

- Lưu ý: Trong trường hợp đoán đúng phần text của khái niệm nhưng sai loại (VD: đoán `CHẨN_ĐOÁN` nhưng ground truth là `TRIỆU_CHỨNG`), khái niệm sẽ bị tính 2 lần (do tạo ra 1 khái niệm mới so với ground truth) và mỗi lần đều được tính 0 điểm với cả 3 loại metric.

# Tài nguyên

Cấu hình máy được sử dụng:

- Thí sinh tự chuẩn bị tài nguyên tính toán. Tuy nhiên, với những giải pháp LLM/agent chỉ cho phép thí sinh self-host model mà không được sử dụng API ngoài, model self-host có độ lớn tối đa là 9B params.
