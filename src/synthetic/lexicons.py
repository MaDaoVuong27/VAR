# -*- coding: utf-8 -*-
"""Lexicon thủ công cho các type KB không có sẵn (triệu chứng, tên xét nghiệm, đơn vị).

Gom từ quan sát 100 sample thật (EDA) + thuật ngữ lâm sàng VN phổ biến. Dùng để sinh
synthetic — KHÔNG phải nhãn test. Mở rộng dần khi thấy type mới.
"""

# Triệu chứng thường gặp (bổ sung cho ICD chương R). Cả VN lẫn vài EN (code-switch).
SYMPTOMS_VI = [
    "sốt", "ho", "ho khan", "ho đờm", "ho ra máu", "khó thở", "khó thở khi gắng sức",
    "khó thở về đêm", "đau ngực", "tức ngực", "đau bụng", "đau thượng vị", "đau đầu",
    "đau đầu dữ dội", "chóng mặt", "buồn nôn", "nôn", "nôn ra máu", "tiêu chảy",
    "táo bón", "mệt mỏi", "mệt mỏi toàn thân", "yếu", "yếu cơ", "sụt cân", "chán ăn",
    "ăn uống kém", "mất ngủ", "lo âu", "hồi hộp", "đánh trống ngực", "ngất", "ngất xỉu",
    "phù", "phù chân", "phù mắt cá chân", "chóng mặt", "hoa mắt", "ù tai", "khàn tiếng",
    "khó nuốt", "nuốt nghẹn", "ợ hơi", "ợ chua", "đầy bụng", "khò khè", "tiếng rít",
    "nghẹt mũi", "chảy nước mũi", "đau họng", "phát ban", "ngứa", "ngứa toàn thân",
    "vàng da", "tê bì", "run tay", "co giật", "lú lẫn", "ảo giác", "mất trí nhớ",
    "đau lưng", "đau khớp", "sưng khớp", "cứng khớp", "tiểu buốt", "tiểu rắt",
    "tiểu ra máu", "tiểu khó", "đổ mồ hôi", "ớn lạnh", "rét run", "mất thăng bằng",
]
SYMPTOMS_EN = ["nausea", "diarrhea", "abdominal pain", "fatigue", "dyspnea", "fever",
               "chest pain", "headache", "dizziness", "cough", "vomiting", "edema"]

# Tên xét nghiệm: cận lâm sàng + chẩn đoán hình ảnh + chỉ số máu
TEST_NAMES = [
    "công thức máu", "tổng phân tích tế bào máu", "bạch cầu", "hồng cầu", "tiểu cầu",
    "WBC", "NEUT%", "LYMPH%", "hemoglobin", "hematocrit", "creatinine", "creatinin",
    "ure", "ure máu", "bun", "glucose", "đường huyết", "hba1c", "troponin", "inr",
    "alt", "ast", "men gan", "bilirubin", "kali", "natri", "kali máu", "crp", "bnp",
    "chức năng gan", "chức năng thận", "điện giải đồ", "tổng phân tích nước tiểu",
    "x-quang ngực", "chụp x-quang ngực", "ct sọ não", "chụp cắt lớp vi tính",
    "mri", "cộng hưởng từ", "siêu âm", "siêu âm bụng", "siêu âm tim", "siêu âm doppler",
    "điện tâm đồ", "ecg", "nội soi", "nội soi dạ dày", "sinh thiết", "chọc hút bằng kim nhỏ",
    "monitor holter", "khí máu động mạch", "chức năng đông máu",
]

# Đơn vị cho KẾT_QUẢ_XÉT_NGHIỆM
UNITS = ["", "", "mg/dl", "mmol/l", "g/l", "g/dl", "%", "U/L", "mEq/L", "ng/ml",
         "µmol/l", "/µL", "mmHg", "bpm", "°C"]

# Cụm kết quả dạng chữ (không phải số) — hay gặp trong data
RESULT_PHRASES = ["bình thường", "không ghi nhận bất thường", "âm tính", "dương tính",
                  "hẹp nặng", "tăng nhẹ", "trong giới hạn bình thường", "không đáng chú ý"]

# Đường dùng / dạng thuốc (để sinh mention thuốc giống test)
DRUG_ROUTES = ["po", "iv", "im", "po daily", "po bid", "po qd", "iv x1", "tiêm tĩnh mạch",
               "uống", "po q6h:prn", "nebs", "po tid"]
DRUG_DOSES = ["5mg", "10 mg", "25mg", "40 mg", "50 mg", "81 mg", "100mg", "325 mg",
              "500mg", "1g", "0.5 mg", "20mg", "2.5mg"]

# Cue assertion
HIST_CUES = ["tiền sử", "tiền sử bệnh", "trước khi nhập viện", "trong quá khứ", "tiền căn"]
NEG_CUES = ["không", "chưa", "không có", "không ghi nhận"]
FAMILY_CUES = ["mẹ bệnh nhân", "bố bệnh nhân", "trong gia đình có người", "anh trai bệnh nhân",
               "chị gái bệnh nhân"]
