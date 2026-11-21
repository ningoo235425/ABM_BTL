# ABM – Phản ứng của ngân hàng trước chỉ đạo giảm lãi suất

## 1. Giới thiệu dự án

Dự án xây dựng mô hình mô phỏng dựa trên tác nhân (Agent-Based Model – ABM) nhằm phân tích phản ứng của các ngân hàng thương mại trước chính sách chỉ đạo giảm lãi suất cho vay.

Mô hình được phát triển bằng **Python và Mesa 3.3.1**, sử dụng dữ liệu khởi tạo của **8 ngân hàng thương mại Việt Nam** và triển khai ba kịch bản chính sách A/B/C.

**Thông tin mô hình hiện tại:**

| Nội dung | Cấu hình |
|---|---|
| Số ngân hàng | 8 |
| Kỳ khởi tạo | Q1/2023 |
| Tần suất mô phỏng | 1 bước = 1 quý |
| Số bước | 18 |
| Thời gian mô phỏng | Q2/2023–Q3/2027 |
| Thời điểm chính sách bắt đầu | Bước 15 – Q4/2026 |
| Số lần chạy mặc định | 60 lần/kịch bản |
| Phân tích độ nhạy nâng cao | 20 lần/cấu hình |
| Ngôn ngữ | Python |
| Thư viện ABM | Mesa 3.3.1 |

**Lưu ý:** Các tham số hiện tại chủ yếu là giả định và chưa được hiệu chỉnh thực nghiệm. Mốc Q4/2026 là thời điểm kích hoạt chính sách trong mô phỏng theo quý.

---

## 2. Hướng dẫn cài đặt và chạy chương trình

### Bước 1 – Mở thư mục dự án

Mở thư mục `ABM_LaiSuat_Vu` bằng VS Code.

Mở Terminal hoặc PowerShell tại thư mục gốc, nơi chứa file `main.py`.

### Bước 2 – Tạo môi trường Python

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Nếu đã có môi trường `.venv` hoạt động thì không cần tạo lại.

### Bước 3 – Cài đặt thư viện

```powershell
python -m pip install -r requirements.txt
```

Yêu cầu có file `requirements.txt` ở thư mục gốc.

### Bước 4 – Chạy toàn bộ chương trình

```powershell
python main.py
```

Đây là **lệnh chạy chính được khuyến nghị**.

Chương trình lần lượt:

1. Chạy mô phỏng ba kịch bản A/B/C.
2. Tổng hợp kết quả trung bình và các phân vị.
3. Phân tích sự khác biệt giữa các nhóm ngân hàng.
4. Phân tích truyền dẫn chính sách.
5. Phân tích độ nhạy các tham số.
6. Đối chiếu dữ liệu lịch sử.
7. Kiểm tra độ trễ và phân tích sai lệch lịch sử.
8. Xuất các bảng dữ liệu và biểu đồ.

### Chạy riêng từng chương trình

**Chỉ chạy kịch bản A/B/C:**

```powershell
python -m src.analysis.experiments --banks data/clean/abm_initial_8nganhang_2023Q1.csv --runs 60
```

**Chỉ chạy phân tích nâng cao A/B/C/D:**

```powershell
python -m src.analysis.advanced_analysis --banks data/clean/abm_initial_8nganhang_2023Q1.csv --runs 60 --sensitivity-runs 20
```

**Chạy bộ kiểm thử:**

```powershell
python -m pytest -v
```

**Kiểm tra tính hợp lệ của mô hình:**

```powershell
python -m src.analysis.validation --banks data/clean/abm_initial_8nganhang_2023Q1.csv
```

---

## 3. Hướng dẫn thay đổi tham số – Dành cho Huy

### 3.1. File cần chỉnh sửa

Để thay đổi các tham số chính của mô hình, mở:

`configs/scenarios.yaml`

Ví dụ:

```yaml
n_months: 18
n_runs: 60
base_seed: 202611

parameters:
  policy_month: 14
  policy_pressure: 0.65
  policy_step: 0.28

  depositor_sensitivity: 0.035
  borrower_elasticity: 0.012
  pass_through: 0.48

  deposit_competition: 0.07
  deposit_cap_factor: 0.25
  max_loan_to_deposit: 1.60

  # Hằng số hành vi (giá trị giả định, chưa hiệu chỉnh)
  base_deposit_rate_step: 0.018
  loan_spread_add: 1.35
  borrower_reference_rate: 9.5
  borrower_base_growth: 0.006
  margin_floor: 2.2

  # Học thích nghi (tùy chọn, mặc định TẮT)
  adaptive_learning: false
  learning_up_step: 0.05
  learning_down_step: 0.10
  learning_growth_threshold: 0.006
  learning_nim_threshold: 5.5875
  learning_rule: absolute
  learning_deadband: 0.005
  learning_benchmark: simple
  learning_nim_condition: true
  margin_min: 2.2
  margin_max: 4.2

sensitivity_relative_width: 0.30
```

### 3.2. Ý nghĩa các tham số

| Tham số | Ý nghĩa |
|---|---|
| `pass_through` | Tốc độ điều chỉnh lãi suất cho vay theo lãi suất mục tiêu dựa trên chi phí vốn trễ |
| `depositor_sensitivity` | Mức phản ứng của tiền gửi với chênh lệch lãi suất huy động |
| `borrower_elasticity` | Mức phản ứng của nhu cầu tín dụng với lãi suất cho vay |
| `policy_pressure` | Áp lực chính sách ảnh hưởng đến xác suất tuân thủ |
| `policy_step` | Mức giảm lãi suất khi ngân hàng tuân thủ chính sách |
| `deposit_competition` | Mức cạnh tranh lãi suất huy động |
| `deposit_cap_factor` | Hệ số hạn chế điều chỉnh tăng lãi suất huy động trong kịch bản C |
| `max_loan_to_deposit` | Giới hạn kỹ thuật dư nợ/tiền gửi của mô hình |
| `policy_month` | Tham số xác định thời điểm bắt đầu can thiệp |
| `sensitivity_relative_width` | Phạm vi phân tích độ nhạy quanh giá trị cơ sở |
| `base_deposit_rate_step` | Mức tăng cơ sở của lãi suất huy động, điểm %/năm **mỗi quý** (trước đây cứng `0.018`) |
| `loan_spread_add` | Biên cộng thêm vào lãi suất cho vay mục tiêu, điểm % (trước đây cứng `1.35`) |
| `borrower_reference_rate` | Lãi suất cho vay tham chiếu của khối người vay, %/năm (trước đây cứng `9.5`) |
| `borrower_base_growth` | Tăng trưởng dư nợ cơ sở tại lãi suất tham chiếu, tỷ lệ **mỗi quý** (trước đây cứng `0.006`) |
| `margin_floor` | Biên `nim_proxy` tham chiếu trong xác suất tuân thủ của NHNN, điểm % (trước đây cứng `2.2`) |
| `adaptive_learning` | Bật/tắt học thích nghi của ngân hàng (`false` = kết quả giống bản cũ) |
| `learning_up_step` | Bước tăng `target_margin` mỗi quý, điểm % (khởi điểm 0.05, **chưa hiệu chỉnh, chờ Huy duyệt**) |
| `learning_down_step` | Bước giảm `target_margin` mỗi quý, điểm % (khởi điểm 0.10, **chưa hiệu chỉnh**) |
| `learning_growth_threshold` | g\*: ngưỡng tăng trưởng dư nợ quý để được tăng biên (0.006, **chưa hiệu chỉnh**) |
| `learning_nim_threshold` | n\*: ngưỡng `nim_proxy` để được tăng biên, điểm %/năm; cố định 5.5875 = bình quân gia quyền theo dư nợ tại t=0 |
| `learning_rule` | `absolute` (mặc định, ngưỡng g\*, n\*) hoặc `relative` (so với bình quân hệ thống) |
| `learning_deadband` | θ: vùng chết quanh tăng trưởng bình quân hệ thống, tỷ lệ/quý (0.005, **chưa hiệu chỉnh, chờ Huy duyệt**); chỉ dùng khi `relative` |
| `learning_benchmark` | Mốc hệ thống của `relative`: `simple` (bình quân đơn giản 8 NH, mặc định, chờ Huy duyệt) hoặc `weighted` (gia quyền dư nợ) |
| `learning_nim_condition` | `relative`: `true` thì chỉ tăng biên khi `nim_proxy` của NH ≥ bình quân hệ thống |
| `margin_min`, `margin_max` | Sàn và trần của `target_margin`, điểm % (2.2 và 4.2, **chưa hiệu chỉnh**) |

Chi tiết cơ chế học: `docs/nang_cap_hoc_thich_nghi.md`. Chạy bản bật học: `python main.py --config configs/scenarios_adaptive.yaml` (file ghi đè: `load_config` luôn nạp `scenarios.yaml` rồi trộn đệ quy file này lên trên, nên file chỉ chứa khóa khác biệt). Chẩn đoán độ nhạy θ/benchmark: `python -m src.analysis.relative_sensitivity --seeds 10` (kết quả trong `docs/nang_cap_hoc_thich_nghi.md` mục 6). Quy tắc relative: `configs/scenarios_adaptive_relative.yaml` và `configs/scenarios_adaptive_relative_nonim.yaml` (không điều kiện nim); cả hai chưa hiệu chỉnh.

### 3.3. Cách thay đổi tham số

Ví dụ, nếu muốn thay đổi hệ số `pass_through` từ 0.48 thành 0.60:

**Giá trị cũ:**

```yaml
pass_through: 0.48
```

**Giá trị mới:**

```yaml
pass_through: 0.60
```

Lưu file YAML và chạy lại:

```powershell
python main.py
```

Chương trình sẽ sử dụng bộ tham số mới.

### 3.4. Phân tích độ nhạy tự động

Hai chương trình `experiments.py` và `advanced_analysis.py` đều sử dụng hàm tạo dải độ nhạy chung trong:

`src/analysis/sensitivity_grid.py`

Khi `sensitivity_relative_width: 0.30`, chương trình tự tạo ba mức bằng 70%, 100% và 130% giá trị cơ sở, có giới hạn hợp lệ đối với các tham số được khảo sát.

Ví dụ, với:

```yaml
pass_through: 0.60
```

Ba mức độ nhạy sẽ là:

| Mức | Giá trị |
|---|---:|
| Thấp | 0.42 |
| Cơ sở | 0.60 |
| Cao | 0.78 |

**Huy không cần chỉnh thủ công các dải độ nhạy trong file Python.**

### 3.5. Những điểm cần lưu ý khi điều chỉnh

- Chỉ thay đổi những tham số đã được nhóm thống nhất.
- Giữ đúng đơn vị và phạm vi giá trị hợp lệ.
- Không tự thay đổi công thức hành vi khi chỉ muốn hiệu chỉnh tham số.
- Những hằng số như `base_growth`, `target_margin`, `reference_rate`, `1.35` và `0.018` hiện vẫn cố định trong mã nguồn tác nhân.
- Nếu thay đổi các hằng số hoặc công thức này, cần ghi rõ phiên bản và kiểm thử lại.
- Không lựa chọn tham số chỉ nhằm tạo ra kết quả mô phỏng mong muốn.

**Sau mỗi lần thay đổi tham số, nên chạy lại `validation.py` và `main.py` để kiểm tra kết quả.**

---

## 4. Kết quả chương trình được lưu ở đâu?

Tất cả kết quả được lưu trong:

`outputs/`

Mỗi lần chạy sẽ tạo các thư mục kết quả riêng theo thời điểm thực hiện.

### 4.1. Thư mục `_KichBan`

Chứa kết quả mô phỏng ba kịch bản A/B/C.

| File | Nội dung |
|---|---|
| `fig_scenarios.png` | Biểu đồ so sánh diễn biến lãi suất A/B/C |
| `bang_ket_qua.csv` | Kết quả thống kê theo kịch bản |
| `runs_A.csv` | Kết quả các lần chạy kịch bản A |
| `runs_B.csv` | Kết quả các lần chạy kịch bản B |
| `runs_C.csv` | Kết quả các lần chạy kịch bản C |
| `sensitivity.csv` | Kết quả độ nhạy trong chương trình mô phỏng |

### 4.2. Thư mục `_PhanTichABC`

Chứa kết quả phân tích nâng cao A/B/C/D.

**Các biểu đồ chính:**

| Biểu đồ | Ý nghĩa |
|---|---|
| `A_loan_rate_nhom.png` | So sánh lãi suất cho vay giữa các nhóm ngân hàng |
| `B_chuyen_dan_chinh_sach.png` | So sánh chênh lệch lãi suất giữa các kịch bản |
| `C_do_nhay.png` | Đánh giá độ nhạy của kết quả với các tham số |
| `C_thuc_te_vs_mo_phong.png` | So sánh lãi suất quan sát và mô phỏng |
| `D1_kiem_tra_do_tre.png` | Kiểm tra phản ứng trễ của lãi suất cho vay |
| `D2_sai_lech_lich_su_theo_quy.png` | Phân tích sai lệch lịch sử theo từng quý |

**Các bảng dữ liệu quan trọng:**

| File | Nội dung |
|---|---|
| `A_du_lieu_tung_ngan_hang.csv` | Dữ liệu mô phỏng theo từng ngân hàng |
| `A_nhom_ngan_hang.csv` | Chỉ tiêu theo nhóm ngân hàng |
| `B_chuyen_dan_trung_binh.csv` | Chênh lệch chính sách bình quân |
| `B_tuan_thu_chinh_sach.csv` | Thông tin tuân thủ chính sách |
| `C_bang_do_nhay.csv` | Bảng phân tích độ nhạy |
| `C_so_sanh_thuc_te.csv` | Đối chiếu lãi suất thực tế và mô phỏng |
| `C_sai_so.csv` | Chỉ tiêu MAE và RMSE |
| `D_kiem_tra_nhiem_vu_4_4.json` | Kết quả kiểm tra độ trễ và hiện tượng đặc trưng |
| `D_chi_tiet_sai_lech_lich_su.csv` | Phân tích sai lệch lịch sử từng quý |

Để xem kết quả của lần chạy mới nhất, mở hai thư mục `_KichBan` và `_PhanTichABC` có thời điểm tạo tương ứng gần nhất.

---

## 5. Cấu trúc thư mục dự án

```text
ABM_LaiSuat_Vu/
│
├── main.py
├── requirements.txt
├── README.md
│
├── configs/
│   ├── scenarios.yaml
│   ├── scenarios_adaptive.yaml
│   ├── scenarios_adaptive_relative.yaml
│   └── scenarios_adaptive_relative_nonim.yaml
│
├── data/
│   └── clean/
│       ├── abm_initial_8nganhang_2023Q1.csv
│       ├── abm_initial_8nganhang_2026Q3.csv
│       └── abm_panel_8nganhang_2023Q1_2026Q3.csv
│
├── src/
│   ├── agents/
│   │   ├── bank.py
│   │   ├── regulator.py
│   │   ├── depositors.py
│   │   └── borrowers.py
│   │
│   ├── core/
│   │   └── model.py
│   │
│   ├── analysis/
│   │   ├── experiments.py
│   │   ├── advanced_analysis.py
│   │   ├── sensitivity_grid.py
│   │   └── validation.py
│   │
│   └── utils/
│       └── output_utils.py
│
├── tests/
├── outputs/
├── docs/
└── report/
```

## 6. Muốn đọc thêm thông tin thì xem ở đâu?

README chỉ hướng dẫn sử dụng chương trình. Các tài liệu chi tiết hơn gồm:

| File / Thư mục | Nội dung |
|---|---|
| `docs/ban_giao_cho_Huy_Minh.md` | Công việc đã thực hiện, chức năng các file, ý nghĩa các biểu đồ và những nội dung cần Huy/Minh xác nhận |
| `report/bao_cao.md` | Dự thảo nội dung báo cáo nghiên cứu, giả định, phân tích và giới hạn mô hình |
| `configs/scenarios.yaml` | Giá trị các tham số và cấu hình chạy |
| `src/agents/` | Công thức và quy tắc hành vi của các tác nhân |
| `src/core/model.py` | Trình tự tương tác và cập nhật của toàn bộ mô hình |
| `src/analysis/` | Phương pháp chạy kịch bản, phân tích độ nhạy, đối chiếu và kiểm tra |
| `tests/` | Các bài kiểm thử tự động |
| `outputs/` | Các bảng kết quả và biểu đồ mô phỏng |

Nếu muốn hiểu **công thức hoạt động**, đọc `src/agents/` và `src/core/model.py`.

Nếu muốn hiểu **ý nghĩa kinh tế của biểu đồ và kết quả**, đọc `docs/ban_giao_cho_Huy_Minh.md` và `report/bao_cao.md`.

Nếu muốn **thay đổi tham số và chạy lại**, sử dụng `configs/scenarios.yaml` và `python main.py`.

---

## 7. Một số lưu ý quan trọng

**Về đơn vị và thời gian**

- Lãi suất cho vay và huy động sử dụng đơn vị %/năm.
- Một bước mô phỏng tương ứng một quý.
- Q1/2023 là trạng thái khởi tạo, bước 1 tương ứng Q2/2023.
- Một số tên biến như `month`, `n_months`, `policy_month` và `finish_month` được giữ để tương thích với code cũ nhưng có ngữ nghĩa theo bước quý.

**Về các chỉ tiêu mô hình**

- `nim_proxy` không đồng nhất với NIM trong báo cáo tài chính.
- `max_loan_to_deposit` là giới hạn kỹ thuật, không phải LDR pháp lý.
- Phân nhóm ngân hàng chỉ mang tính tương đối trong mẫu 8 ngân hàng.
- Các hệ số tăng trưởng cơ sở hiện là giả định theo quý, chưa được hiệu chỉnh từ dữ liệu thực nghiệm.

**Về kết quả nghiên cứu**

- Mô hình được sử dụng để phân tích phản ứng trong các kịch bản giả định.
- Kết quả A/B/C không mặc nhiên thể hiện tác động chính sách thực tế.
- MAE/RMSE hiện phản ánh đối chiếu lịch sử, chưa phải đánh giá ngoài mẫu.
- Dữ liệu quan sát mới đến Q3/2026 nên chưa thể kiểm chứng thực nghiệm phản ứng sau mốc chính sách giả định Q4/2026.
- Trước khi báo cáo kết quả cuối cùng, cần phối hợp với Huy và Minh để xác nhận quy tắc hành vi, nguồn dữ liệu và bộ tham số hiệu chỉnh.

---

## 8. Hướng dẫn nhanh

| Muốn làm gì? | Thao tác |
|---|---|
| Chạy toàn bộ mô hình | `python main.py` |
| Kiểm thử code | `python -m pytest -v` |
| Kiểm tra logic mô hình | `python -m src.analysis.validation --banks data/clean/abm_initial_8nganhang_2023Q1.csv` |
| Thay đổi tham số | Mở `configs/scenarios.yaml` |
| Xem kết quả A/B/C | Mở `outputs/*_KichBan/` |
| Xem phân tích A/B/C/D | Mở `outputs/*_PhanTichABC/` |
| Xem tài liệu bàn giao | Mở `docs/ban_giao_cho_Huy_Minh.md` |
| Xem báo cáo nghiên cứu | Mở `report/bao_cao.md` |

**Quy trình khuyến nghị:** Chỉnh tham số trong YAML → chạy kiểm thử và validation → chạy `python main.py` → mở thư mục kết quả mới nhất → đối chiếu với bộ kết quả trước đó → lưu lại cấu hình đã sử dụng.