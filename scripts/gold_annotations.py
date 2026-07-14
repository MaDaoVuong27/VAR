# -*- coding: utf-8 -*-
"""Annotation gold ĐỘC LẬP cho 15 file dev (do assistant đọc & gán, v1 — cần người verify).

Mỗi concept: dict {t: text (substring đúng raw), y: type, a: assertions, c: candidates,
  after: (tuỳ chọn) anchor để nhảy cursor tới đúng vùng, occ: (tuỳ chọn) occurrence thứ n}.
Liệt kê theo THỨ TỰ ĐỌC để helper tính offset bằng cursor tuần tự.

Candidate:
- CHẨN_ĐOÁN -> mã ICD-10 (theo kiến thức lâm sàng; một số ca khó để []).
- THUỐC -> RxCUI hoạt chất (exact lookup, granularity ingredient — có thể khác SCD official).
Ghi chú: đây là v1, độ tin candidate < spans/types/assertions. Người verify sẽ chỉnh.
"""
from src.schema import (
    TYPE_CHAN_DOAN as DX,
    TYPE_THUOC as DRUG,
    TYPE_TRIEU_CHUNG as SYM,
    TYPE_TEN_XN as LABN,
    TYPE_KQ_XN as LABV,
)

H = ["isHistorical"]
N = ["isNegated"]
F = ["isFamily"]
HN = ["isHistorical", "isNegated"]

GOLD = {
    # ---------------- 31: ngắn, sản khoa, freeform, viết tắt ----------------
    "31": [
        {"t": "cơn co tử cung", "y": SYM, "a": []},
        {"t": "ra huyết âm đạo", "y": SYM, "a": N},
        {"t": "vỡ ối", "y": SYM, "a": N},
        {"t": "rỉ ối", "y": SYM, "a": N},
    ],
    # ---------------- 6: PROSE canary — văn xuôi, baseline rỗng ----------------
    "6": [
        {"t": "Nghẽn tắc và hẹp động mạch cảnh", "y": DX, "a": H, "c": ["I65.2"]},
        {"t": "siêu âm Doppler động mạch", "y": LABN, "a": []},
        {"t": "siêu âm doppler hai chiều", "y": LABN, "a": []},
        {"t": "hẹp nặng", "y": LABV, "a": []},
        {"t": "tỷ số PSV/EDV > 7", "y": LABV, "a": []},
        {"t": "vận tốc dòng chảy tăng rõ", "y": LABV, "a": []},
    ],
    # ---------------- 8: PROSE canary — phủ định trong câu, baseline rỗng ----------------
    "8": [
        {"t": "nốt tuyến giáp thùy trái", "y": DX, "a": [], "c": ["E04.1"]},
        {"t": "chọc hút bằng kim nhỏ", "y": LABN, "a": [], "after": "thủ thuật chọc hút"},
        {"t": "tế bào học", "y": LABN, "a": [], "after": "Kết quả xét nghiệm tế bào học"},
        {"t": "bất thường", "y": LABV, "a": [], "after": "ghi nhận bất thường"},
        {"t": "khó nuốt", "y": SYM, "a": N},
        {"t": "khó thở", "y": SYM, "a": N},
        {"t": "khàn tiếng", "y": SYM, "a": N},
    ],
    # ---------------- 36: ghép thận, thuốc ức chế miễn dịch ----------------
    "36": [
        {"t": "Bệnh thận đa nang", "y": DX, "a": H, "c": ["Q61.3"]},
        {"t": "azathioprine", "y": DRUG, "a": H, "c": ["1256"]},
        {"t": "prograf", "y": DRUG, "a": H, "c": ["42316"]},
        {"t": "cellcept", "y": DRUG, "a": H, "c": ["68149"]},
        {"t": "Suy thận", "y": DX, "a": [], "c": ["N19"]},
        {"t": "creatinine", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "5.1", "y": LABV, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "k", "y": LABN, "a": [], "after": "creatinine 5.1"},
        {"t": "5.8", "y": LABV, "a": [], "after": "creatinine 5.1"},
        {"t": "Bệnh lý thận do BK", "y": DX, "a": [], "c": []},
    ],
    # ---------------- 35: CML + nhiều bệnh mạn + lab ----------------
    "35": [
        {"t": "Bệnh bạch cầu dòng tủy mãn tính", "y": DX, "a": H, "c": ["C92.1"]},
        {"t": "gleevec", "y": DRUG, "a": H, "c": ["282388"]},
        {"t": "Tăng huyết áp", "y": DX, "a": H, "c": ["I10"]},
        {"t": "tăng lipid máu, không đặc hiệu", "y": DX, "a": H, "c": ["E78.5"]},
        {"t": "Đái tháo đường típ 2", "y": DX, "a": H, "c": ["E11"]},
        {"t": "hẹp ống sống", "y": DX, "a": H, "c": ["M48.0"]},
        {"t": "Giả gout", "y": DX, "a": H, "c": ["M11.2"]},
        {"t": "tăng sản tuyến tiền liệt", "y": DX, "a": H, "c": ["N40"]},
        {"t": "ảo giác", "y": SYM, "a": H},
        {"t": "toàn trạng suy kiệt", "y": SYM, "a": []},
        {"t": "ảo giác", "y": SYM, "a": [], "after": "Triệu chứng hiện tại"},
        {"t": "Lú lẫn", "y": SYM, "a": []},
        {"t": "bạch cầu", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "39.2", "y": LABV, "a": []},
        {"t": "creatinin", "y": LABN, "a": [], "after": "39.2"},
        {"t": "3.0", "y": LABV, "a": []},
        {"t": "troponin", "y": LABN, "a": []},
        {"t": "0.10", "y": LABV, "a": []},
    ],
    # ---------------- 37: suy tim/CKD, nhiều thuốc ngừng, lab ----------------
    "37": [
        {"t": "Tăng huyết áp", "y": DX, "a": H, "c": ["I10"]},
        {"t": "Đái tháo đường, có biến chứng bệnh lý thần kinh ngoại biên", "y": DX, "a": H, "c": ["E11.4"]},
        {"t": "Suy tim", "y": DX, "a": H, "c": ["I50.9"]},
        {"t": "Bệnh thận mạn tính", "y": DX, "a": H, "c": ["N18.9"]},
        {"t": "Torsemide", "y": DRUG, "a": H, "c": ["38413"]},
        {"t": "Insulin glargine", "y": DRUG, "a": H, "c": ["274783"]},
        {"t": "Isosorbide", "y": DRUG, "a": H, "c": ["6057"]},
        {"t": "Rosuvastatin (Crestor)", "y": DRUG, "a": H, "c": ["301542"]},
        {"t": "Carvedilol", "y": DRUG, "a": H, "c": ["20352"]},
        {"t": "tăng kali máu", "y": DX, "a": [], "c": ["E87.5"]},
        {"t": "kali", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "6.3", "y": LABV, "a": []},
        {"t": "ure (bun)", "y": LABN, "a": []},
        {"t": "83", "y": LABV, "a": []},
        {"t": "creatinine", "y": LABN, "a": [], "after": "ure (bun) 83"},
        {"t": "5.7", "y": LABV, "a": []},
        {"t": "hemoglobin", "y": LABN, "a": []},
        {"t": "7.8", "y": LABV, "a": []},
        {"t": "iv lasix 40 mg once", "y": DRUG, "a": [], "c": ["4603"]},
    ],
    # ---------------- 50: hen, thuốc, triệu chứng hô hấp ----------------
    "50": [
        {"t": "hen suyễn", "y": DX, "a": H, "c": ["J45"], "after": "Bệnh mạn tính"},
        {"t": "albuterol nebs q4h tại nhà", "y": DRUG, "a": H, "c": ["435"]},
        {"t": "z-pack", "y": DRUG, "a": H, "c": ["18631"]},
        {"t": "khó thở", "y": SYM, "a": [], "after": "Lý do nhập viện"},
        {"t": "tiếng rít", "y": SYM, "a": []},
        {"t": "prednisone", "y": DRUG, "a": [], "c": ["8640"]},
        {"t": "amoxicillin", "y": DRUG, "a": [], "c": ["723"]},
        {"t": "azithromycin", "y": DRUG, "a": [], "c": ["18631"]},
        {"t": "đau đầu dữ dội", "y": SYM, "a": []},
        {"t": "Khó thở", "y": SYM, "a": [], "after": "Triệu chứng khi nhập viện"},
        {"t": "Khò khè", "y": SYM, "a": []},
        {"t": "Đau vùng xoang", "y": SYM, "a": []},
        {"t": "Mất ngủ", "y": SYM, "a": []},
    ],
    # ---------------- 51: hạ kali máu + tiêu chảy ----------------
    "51": [
        {"t": "Đái tháo đường type 2", "y": DX, "a": H, "c": ["E11"]},
        {"t": "Tăng huyết áp", "y": DX, "a": H, "c": ["I10"]},
        {"t": "cảm thấy khó chịu chung", "y": SYM, "a": []},
        {"t": "nghẹt mũi nhiều hơn", "y": SYM, "a": []},
        {"t": "đau đầu bên trái", "y": SYM, "a": []},
        {"t": "mệt mỏi", "y": SYM, "a": []},
        {"t": "tiêu chảy", "y": SYM, "a": []},
        {"t": "azithromycin", "y": DRUG, "a": [], "c": ["18631"]},
        {"t": "kali", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "2.4", "y": LABV, "a": []},
        {"t": "hạ kali máu", "y": DX, "a": [], "c": ["E87.6"]},
    ],
    # ---------------- 54: (đọc file để annotate riêng — dài) placeholder rỗng an toàn ----------------
    # 54 chưa annotate kỹ ở v1 (dài, để trống -> không tính điểm file này)
    # ---------------- 66: nhiều bệnh mạn + lab, code-switch ----------------
    "66": [
        {"t": "Tiểu đường loại 1 đái tháo đường", "y": DX, "a": H, "c": ["E10"]},
        {"t": "tăng huyết áp", "y": DX, "a": H, "c": ["I10"]},
        {"t": "tăng lipid máu, không đặc hiệu", "y": DX, "a": H, "c": ["E78.5"]},
        {"t": "béo phì", "y": DX, "a": H, "c": ["E66.9"]},
        {"t": "đau bàn chân phải", "y": SYM, "a": []},
        {"t": "mất thăng bằng khi đi lại", "y": SYM, "a": []},
        {"t": "viêm bể thận", "y": DX, "a": H, "c": ["N10"]},
        {"t": "viêm phế quản", "y": DX, "a": H, "c": ["J40"]},
        {"t": "ertapenem", "y": DRUG, "a": H, "c": ["325642"]},
        {"t": "tiểu cầu (platelets)", "y": LABN, "a": []},
        {"t": "478", "y": LABV, "a": []},
        {"t": "glucose (đường huyết)", "y": LABN, "a": []},
        {"t": "316", "y": LABV, "a": []},
    ],
    # ---------------- 70: đau bụng gan mật + acetaminophen ----------------
    "70": [
        {"t": "acetaminophen 500mg", "y": DRUG, "a": H, "c": ["161"]},
        {"t": "đau bụng ngày càng nặng", "y": SYM, "a": []},
        {"t": "mệt mỏi toàn thân", "y": SYM, "a": []},
        {"t": "khó thở khi gắng sức", "y": SYM, "a": []},
        {"t": "ngứa toàn thân", "y": SYM, "a": []},
        {"t": "buồn nôn", "y": SYM, "a": N, "after": "Đặc điểm triệu chứng"},
        {"t": "nôn", "y": SYM, "a": N, "after": "Không có buồn nôn"},
        {"t": "ast", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "421", "y": LABV, "a": []},
        {"t": "alt", "y": LABN, "a": []},
        {"t": "336", "y": LABV, "a": []},
        {"t": "tăng men gan", "y": DX, "a": [], "c": ["R74.0"]},
        {"t": "tăng bilirubin máu", "y": DX, "a": [], "c": ["R17"]},
    ],
    # ---------------- 82: CKD5 + ung thư TTL + triệu chứng ure máu ----------------
    "82": [
        {"t": "Suy thận mạn giai đoạn V do đái tháo đường và tăng huyết áp", "y": DX, "a": H, "c": ["N18.5"]},
        {"t": "u ác của tuyến tiền liệt", "y": DX, "a": H, "c": ["C61"]},
        {"t": "mệt mỏi", "y": SYM, "a": [], "after": "Khám hiện tại"},
        {"t": "Ăn không ngon miệng", "y": SYM, "a": []},
        {"t": "Ngứa da toàn thân nhiều", "y": SYM, "a": []},
        {"t": "mất trí nhớ chi tiết", "y": SYM, "a": []},
        {"t": "khó thở khi gắng sức", "y": SYM, "a": []},
        {"t": "buồn nôn và nôn", "y": SYM, "a": []},
        {"t": "creatinine", "y": LABN, "a": []},
        {"t": "6.3", "y": LABV, "a": []},
        {"t": "Ure", "y": LABN, "a": []},
        {"t": "91", "y": LABV, "a": []},
    ],
    # ---------------- 84: FAMILY + nhiều bệnh mạn ----------------
    "84": [
        {"t": "hen suyễn", "y": DX, "a": H, "c": ["J45"]},
        {"t": "rối loạn lo âu", "y": DX, "a": H, "c": ["F41.9"]},
        {"t": "tăng huyết áp", "y": DX, "a": H, "c": ["I10"]},
        {"t": "Táo bón mãn tính", "y": DX, "a": H, "c": ["K59.0"]},
        {"t": "ngưng thở khi ngủ", "y": DX, "a": H, "c": ["G47.3"]},
        {"t": "mệt mỏi", "y": SYM, "a": F, "after": "thành viên trong gia đình"},
        {"t": "ho", "y": SYM, "a": F},
        {"t": "chảy nước mũi", "y": SYM, "a": F},
    ],
    # ---------------- 87: narrator (KHÔNG family), chấn thương tự tử, cắt cụt chi ----------------
    "87": [
        {"t": "trầm cảm", "y": DX, "a": H, "c": ["F32.9"]},
        {"t": "rối loạn lo âu", "y": DX, "a": H, "c": ["F41.9"]},
        {"t": "tổn thương chi dưới", "y": SYM, "a": []},
        {"t": "thuyên tắc phổi hai bên", "y": DX, "a": [], "c": ["I26.9"]},
    ],
    # ---------------- 91: van tim/CKD5, phủ định dày, coumadin/heparin ----------------
    "91": [
        {"t": "Viêm nội tâm mạc", "y": DX, "a": H, "c": ["I33.0"]},
        {"t": "rung nhĩ", "y": DX, "a": H, "c": ["I48"]},
        {"t": "coumadin 3.0 mg /ngày", "y": DRUG, "a": H, "c": ["11289"]},
        {"t": "chảy máu mũi", "y": SYM, "a": []},
        {"t": "Không chảy máu mũi", "y": SYM, "a": N},
        {"t": "đau ngực", "y": SYM, "a": N},
        {"t": "khó thở", "y": SYM, "a": N},
        {"t": "đau bụng", "y": SYM, "a": N},
        {"t": "buồn nôn", "y": SYM, "a": N},
        {"t": "INR", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "1.7", "y": LABV, "a": []},
        {"t": "heparin", "y": DRUG, "a": [], "c": ["5224"]},
    ],
    # ---------------- 97: (đọc file để annotate riêng) — để trống an toàn v1 ----------------
    # ---------------- 3: dài, ngất xỉu, nhiều triệu chứng phủ định ----------------
    "3": [
        {"t": "bệnh tim mạch do xơ vữa động mạch", "y": DX, "a": H, "c": ["I25.1"]},
        {"t": "tăng huyết áp", "y": DX, "a": H, "c": ["I10"]},
        {"t": "phình động mạch chủ nhỏ", "y": DX, "a": H, "c": ["I71.9"]},
        {"t": "cơn ngất xỉu", "y": SYM, "a": [], "after": "Lý do nhập viện"},
        {"t": "Không đánh trống ngực", "y": SYM, "a": N},
        {"t": "Không chóng mặt", "y": SYM, "a": N},
        {"t": "Không buồn nôn", "y": SYM, "a": N},
        {"t": "đau ngực", "y": SYM, "a": []},
        {"t": "khó thở khi gắng sức", "y": SYM, "a": []},
        {"t": "phù mắt cá chân", "y": SYM, "a": []},
        {"t": "troponin", "y": LABN, "a": [], "after": "Kết quả xét nghiệm"},
        {"t": "0.01", "y": LABV, "a": []},
    ],
}
