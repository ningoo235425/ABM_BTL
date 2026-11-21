# Nâng cấp: ngân hàng học thích nghi

> Trạng thái: **tùy chọn, mặc định TẮT** (`adaptive_learning: false`). Mọi tham số học là **giá trị khởi điểm, chưa hiệu chỉnh, chờ Huy duyệt**. Kết quả dưới đây là so sánh trong mẫu của mô hình minh họa, không phải ước lượng tác động chính sách thực tế.

## 1. Cơ chế

Trong mô hình gốc, biên `target_margin` $m_i=3.2$ là hằng số: lãi suất cho vay mục tiêu là $r^*_{i,t}=c_{i,t-1}+m_i+\delta$ với $c$ là chi phí vốn trễ và $\delta=$ `loan_spread_add`. Khi bật học, cuối mỗi quý (trong `Bank.finish_month`) ngân hàng $i$ chỉnh $m_i$ cho quý kế tiếp.

Ký hiệu: $s_{i,t}=L_{i,t}/\sum_j L_{j,t}$ là thị phần dư nợ, $g_{i,t}=L_{i,t}/L_{i,t-1}-1$ là tăng trưởng dư nợ quý, $\text{nim}_{i,t}$ là `nim_proxy` cuối quý.

$$
\Delta_{i,t}=
\begin{cases}
-d & \text{nếu } s_{i,t}<s_{i,t-1}\\[2pt]
+u & \text{nếu } s_{i,t}\ge s_{i,t-1}\ \wedge\ g_{i,t}\ge g^*\ \wedge\ \text{nim}_{i,t}\ge n^*\\[2pt]
0 & \text{còn lại}
\end{cases}
$$

$$
m_{i,t+1}=\min\!\big(m_{\max},\ \max(m_{\min},\ m_{i,t}+\Delta_{i,t})\big)
$$

Khi cả hai điều kiện cùng xảy ra thì chỉ giảm. Giá trị khởi điểm: $u=0.05$, $d=0.10$ (điểm %/quý), $g^*=0.006$ (bằng tăng trưởng cơ sở), $n^*=5.5875$ điểm %/năm, $[m_{\min},m_{\max}]=[2.2,4.2]$. $n^*$ là `nim_proxy` bình quân gia quyền theo dư nợ của 8 ngân hàng tại t=0, tính một lần từ `abm_initial_8nganhang_2023Q1.csv` và ghi cố định trong YAML. Cột `target_margin` mới ở cuối `bank_history` ghi biên đã cập nhật, áp dụng cho quý kế tiếp. Hàm học không dùng số ngẫu nhiên, nên không làm lệch chuỗi RNG.

## 2. Lý do kinh tế

- **Dùng thị phần dư nợ, không dùng thị phần tiền gửi.** `target_margin` chỉ tác động lên lãi suất cho vay và qua đó lên dư nợ; nó không tác động lên tiền gửi (lãi suất huy động và tiền gửi được xác định bởi kênh khác). Dùng thị phần tiền gửi làm tín hiệu sẽ gắn phần thưởng/phạt vào một biến mà quyết định được chỉnh không điều khiển được.
- Mất thị phần cho vay là dấu hiệu giá cho vay kém cạnh tranh, nên giảm biên (bước giảm lớn hơn bước tăng: phản ứng bất đối xứng, mất khách đau hơn).
- Chỉ nới biên khi cùng lúc tăng trưởng tốt và `nim_proxy` cao, tức ngân hàng có dư địa. Bước tăng nhỏ để hành vi thận trọng.
- Biên bị chặn để không trôi ra ngoài miền hợp lý.

## 3. Liên hệ với học thích nghi (Santa Fe Institute)

Cơ chế thuộc họ mô hình *tác nhân thích nghi bị giới hạn lý trí* của kinh tế học tính toán/phức hệ thích nghi (W. B. Arthur, J. Holland, J. Epstein–R. Axtell...): tác nhân không tối ưu hóa mà điều chỉnh quy tắc theo phản hồi từ kết quả gần nhất, và hành vi tổng thể nổi lên từ tương tác. Nó gần nhất với học tăng cường đơn giản/học theo kết quả (win-stay/lose-shift, mô hình Roth–Erev). Khác biệt: mô hình này chỉ có một tham số học trực tiếp, không có quần thể quy tắc cạnh tranh hay tiến hóa như hệ phân loại của Holland, nên là phiên bản rất sơ đẳng. *Đây là liên hệ khái niệm, chưa được kiểm chứng bằng đối chiếu tài liệu trong repo; nhóm cần tự xác nhận trích dẫn trước khi đưa vào báo cáo.*

## 4. Bảng so sánh (10 lần chạy, `--sensitivity-runs 2`, seed gốc 202611)

Lệnh: `python main.py --runs 10 --sensitivity-runs 2` (TẮT) và `python main.py --config configs/scenarios_adaptive.yaml --runs 10 --sensitivity-runs 2` (BẬT). Đơn vị %/năm.

**loan_rate trung bình (gia quyền theo dư nợ)**

| | A | B | C |
|---|---|---|---|
| TẮT, trung bình 18 quý | 8.835 | 8.746 | 8.740 |
| BẬT, trung bình 18 quý | 8.482 | 8.396 | 8.391 |
| TẮT, trung bình Q4/2026–Q3/2027 | 9.038 | 8.637 | 8.611 |
| BẬT, trung bình Q4/2026–Q3/2027 | 8.429 | 8.045 | 8.018 |

**Chênh lệch sau Q4/2026 (điểm %)**

| Quý | B−A (TẮT) | C−A (TẮT) | B−A (BẬT) | C−A (BẬT) |
|---|---|---|---|---|
| Q4/2026 | −0.261 | −0.261 | −0.251 | −0.251 |
| Q1/2027 | −0.391 | −0.402 | −0.373 | −0.389 |
| Q2/2027 | −0.454 | −0.489 | −0.438 | −0.473 |
| Q3/2027 | −0.496 | −0.555 | −0.477 | −0.532 |
| Trung bình | −0.401 | −0.427 | −0.385 | −0.411 |

**loan_rate theo nhóm, trung bình Q4/2026–Q3/2027**

| Kịch bản | Nhóm | TẮT | BẬT |
|---|---|---|---|
| A | quốc doanh | 8.802 | 8.135 |
| A | cổ phần lớn | 8.924 | 8.382 |
| A | cổ phần nhỏ | 10.170 | 9.341 |
| B | quốc doanh | 8.404 | 7.748 |
| B | cổ phần lớn | 8.507 | 7.980 |
| B | cổ phần nhỏ | 9.754 | 8.988 |
| C | quốc doanh | 8.373 | 7.716 |
| C | cổ phần lớn | 8.487 | 7.959 |
| C | cổ phần nhỏ | 9.747 | 8.973 |

Chênh giữa nhóm cao nhất và thấp nhất tại Q3/2027: TẮT A/B/C = 1.329 / 1.323 / 1.378; BẬT = 1.217 / 1.260 / 1.295 (trước chính sách, Q3/2026: TẮT 1.428, BẬT 1.186). Tác động B−A theo nhóm (trung bình Q4/2026–Q3/2027): TẮT −0.417 / −0.398 / −0.416 (cổ phần lớn / quốc doanh / cổ phần nhỏ); BẬT −0.402 / −0.387 / −0.353.

**Biên và tuân thủ (BẬT)**

| Chỉ tiêu | TẮT | BẬT |
|---|---|---|
| `target_margin` trung bình Q3/2027 (lớn / nhỏ / quốc doanh) | 3.2 / 3.2 / 3.2 | 2.42 / 2.35 / 2.43 |
| Tỷ lệ ngân hàng-lần chạy chạm sàn 2.2, Q3/2027 | 0 | 37.5% (3/8 ngân hàng) |
| Chạm trần 4.2 | 0 | 0 |
| Xác suất tuân thủ trung bình (B / C) | 0.939 / 0.941 | 0.878 / 0.882 |
| Tỷ lệ tuân thủ thực tế (B / C) | 0.938 / 0.944 | 0.878 / 0.884 |
| `nim_proxy` trung bình Q4/2026–Q3/2027 (A) | 4.49 | 3.82 |

Kiểm tra mục 6 CLAUDE.md khi BẬT: B và C không cao hơn A ở mọi lần chạy sau Q4/2026; A/B/C trùng nhau ở mọi quý trước chính sách; lãi suất cho vay 7.89–9.10, huy động 4.82–5.78; LDR tối đa 1.23 ≤ 1.60. Không vi phạm.

## 5. Hạn chế

- Mặt bằng lãi suất cho vay giảm ~0.6 điểm % ở A khi bật học; đây là hệ quả của cơ chế, không phải tác động chính sách. Thị phần dư nợ có tổng bằng 1 nên luôn có ngân hàng mất thị phần (tín hiệu giảm kích hoạt thường xuyên), trong khi tín hiệu tăng đòi hỏi `nim_proxy` ≥ n\*; khi lãi suất hội tụ về mức cân bằng (~4.5) `nim_proxy` thấp hơn n\*=5.59 nên bước tăng gần như tắt. Hệ thống có xu hướng trôi về sàn.
- Biên chạm sàn ở 3/8 ngân hàng vào Q3/2027 và tỷ lệ này tăng dần; kết quả phụ thuộc vào sàn 2.2.
- Tất cả tham số học là khởi điểm, chưa hiệu chỉnh theo dữ liệu panel; không có kiểm định ngoài mẫu.
- Một số ít ngân hàng (8) và 10 lần chạy; kịch bản A không có ngẫu nhiên nên các lần chạy giống nhau.
- `nim_proxy` tại t=0 (n\*) phụ thuộc cách định nghĩa chi phí vốn xấp xỉ của mô hình.
- Học làm thay đổi xác suất tuân thủ chỉ đạo (vì xác suất phụ thuộc `nim_proxy`), nên khó tách riêng tác động của chỉ đạo với tác động của học.
- Học chỉ chỉnh biên cho vay; tiền gửi và lãi suất huy động không học.


## 6. Quy tắc học relative và phân tích độ vững (Giai đoạn 5–6)

> **Vai trò trong báo cáo (quyết định của người dùng):** mô hình chính vẫn là **học TẮT**. Quy tắc relative được trình bày như **phân tích độ vững**: kiểm tra kết luận B−A, C−A có đổi khi ngân hàng học thích nghi hay không. Mọi tham số (θ, bước 0.05, benchmark) **chưa hiệu chỉnh, chờ Huy duyệt**.

### 6.1. Kế hoạch và quyết định đã duyệt (để nhóm theo dõi)

**Giai đoạn 4 (chẩn đoán).** Biên trôi của quy tắc absolute do cơ chế: khoảng 0.04–0.06 điểm %/quý, 33–38% ngân hàng chạm sàn 2.2 ở quý 18, hầu như không có bước tăng vì `nim_proxy` < n\* = 5.5875. Hai nguyên nhân nghi ngờ: (1) thị phần có tổng cố định nên luôn có ngân hàng bị giảm biên; (2) n\* lấy từ 2023Q1 không đạt được ở cân bằng.

**Giai đoạn 5 (đã làm, commit 5629ee1).** Thêm `learning_rule: absolute|relative` (mặc định absolute), `learning_deadband` θ = 0.005 (tăng trưởng/quý), `learning_benchmark: simple|weighted` (mặc định simple: bình quân đơn giản 8 ngân hàng, tránh 3 ngân hàng quốc doanh lớn chi phối mốc), `learning_nim_condition` (mặc định true). Công thức, với $\bar g$, $\overline{nim}$ tính **một lần mỗi quý** trước khi ngân hàng nào cập nhật `prev_loans`, không đổi trình tự `step()`, không dùng RNG:

$$
\Delta_{i,t}=
\begin{cases}
-d & g_{i,t} < \bar g_t-\theta\\
+u & g_{i,t} > \bar g_t+\theta\ \wedge\ (\text{nim}_{i,t}\ge \overline{\text{nim}}_t\ \text{nếu bật điều kiện nim})\\
0 & \text{còn lại}
\end{cases}
$$

Lý do kinh tế: so với mốc hệ thống thay vì ngưỡng cố định thì không còn lỗi "ngưỡng không bao giờ đạt", và đo vị thế tương đối thay vì mức tuyệt đối. Cấu hình: `scenarios_adaptive.yaml` (absolute), `scenarios_adaptive_relative.yaml` (có điều kiện nim, bước 0.05 hai chiều), `scenarios_adaptive_relative_nonim.yaml` (không điều kiện nim). `load_config` nạp `scenarios.yaml` rồi trộn đệ quy file ghi đè.

**Giai đoạn 6 (quyết định sau báo cáo reviewer, ĐẠT CÓ ĐIỀU KIỆN).**
1. Mô hình chính = học TẮT; relative = phân tích độ vững.
2. Biến thể không điều kiện nim (relnn) giữ trong code với `xfail(strict)`, chỉ nhắc ở phụ lục như kết quả âm.
3. Test trôi dùng 5 seed, mốc biên lấy từ dữ liệu khởi tạo, giữ ngưỡng ±0.1 cho bình quân các seed (không nới).
4. Độ nhạy θ là **chẩn đoán, không chọn tham số**: `python -m src.analysis.relative_sensitivity --seeds 10` (θ ∈ {0, 0.0025, 0.005, 0.01}, hai bộ dữ liệu, thêm weighted θ = 0.005). Kết quả ghi ở `outputs/relative_sensitivity.csv` (không commit).
5. Chưa chạy lại `main.py --runs 30` cho 4 cấu hình; bảng dưới đây thay cho phần so sánh B−A, C−A.

### 6.2. "Không trôi" là kết quả thực nghiệm, không phải tính chất cấu trúc

Với θ = 0.005 và điều kiện nim, biên trung bình ở kịch bản A gần như không đổi sau 18 quý. Đó là **kết quả thực nghiệm trên dữ liệu này**, do cân bằng giữa hai thiên lệch ngược chiều (điều kiện nim cản bước tăng, kéo biên xuống; phân phối tăng trưởng lệch phải làm phía tăng nhiều hơn khi bỏ điều kiện, kéo biên lên). Tín hiệu $g_i-\bar g$ có trung bình bằng 0 theo định nghĩa (benchmark simple), nên không có bảo đảm cấu trúc. Bảng dưới cho thấy mức trôi đổi dấu và độ lớn theo θ, benchmark và bộ dữ liệu. Biên của từng ngân hàng phân tán mạnh dù trung bình đứng yên (reviewer ghi nhận ở quý 18: Techcombank 4.05, HDBank và Vietcombank 2.70, seed 202611).

### 6.3. Bảng độ nhạy (10 seed 202611–202620, kịch bản A/B/C)

Đơn vị: trôi biên = biên TB quý 18 trừ biên khởi đầu (điểm %); chạm sàn/trần = tỷ lệ ngân hàng **tại quý 18** (không phải mọi quý); B−A, C−A = chênh `loan_rate` TB sau Q4/2026 (tháng > 14), điểm %/năm, bình quân các seed (min–max theo seed, ghép cặp cùng seed). Kịch bản A không dùng RNG nên trôi biên giống nhau giữa các seed (nhiều seed chỉ có tác dụng với B, C).

**Bộ 2023Q1**

| Cấu hình | Trôi biên q18 | Chạm sàn/trần | B−A (min–max) | C−A (min–max) |
|---|---|---|---|---|
| TẮT | 0.0000 | 0 / 0 | −0.4005 (−0.4329 – −0.3515) | −0.4265 (−0.4547 – −0.3902) |
| rel θ = 0 | −0.1500 | 0 / 0 | −0.3987 (−0.4332 – −0.3416) | −0.4234 (−0.4558 – −0.3668) |
| rel θ = 0.0025 | −0.0250 | 0 / 0 | −0.4048 (−0.4371 – −0.3564) | −0.4281 (−0.4591 – −0.3811) |
| rel θ = 0.005 | 0.0000 | 0 / 0 | −0.4005 (−0.4350 – −0.3405) | −0.4270 (−0.4571 – −0.3795) |
| rel θ = 0.01 | +0.0375 | 0 / 0 | −0.4079 (−0.4312 – −0.3738) | −0.4296 (−0.4529 – −0.3955) |
| rel weighted θ = 0.005 | −0.0812 | 0 / 0 | −0.4000 (−0.4336 – −0.3406) | −0.4284 (−0.4558 – −0.3903) |

**Bộ 2026Q3**

| Cấu hình | Trôi biên q18 | Chạm sàn/trần | B−A (min–max) | C−A (min–max) |
|---|---|---|---|---|
| TẮT | 0.0000 | 0 / 0 | −0.4023 (−0.4335 – −0.3569) | −0.4283 (−0.4572 – −0.3806) |
| rel θ = 0 | −0.1000 | 0 / 0 | −0.4129 (−0.4406 – −0.3798) | −0.4384 (−0.4659 – −0.4046) |
| rel θ = 0.0025 | −0.0625 | 0 / 0 | −0.4155 (−0.4441 – −0.3818) | −0.4468 (−0.4739 – −0.4127) |
| rel θ = 0.005 | +0.0375 | 0 / 0 | −0.4093 (−0.4338 – −0.3723) | −0.4332 (−0.4578 – −0.3962) |
| rel θ = 0.01 | +0.0375 | 0 / 0 | −0.4080 (−0.4329 – −0.3718) | −0.4319 (−0.4568 – −0.3957) |
| rel weighted θ = 0.005 | −0.1375 | 0 / 0 | −0.4067 (−0.4341 – −0.3730) | −0.4346 (−0.4631 – −0.3986) |

Nhận xét về trôi biên (ngưỡng tham chiếu ±0.1): trên 2023Q1, θ = 0 (−0.150) vượt ngưỡng; trên 2026Q3, weighted (−0.1375) vượt ngưỡng và θ = 0 sát ngưỡng (−0.100). Các ô còn lại trong ngưỡng. Không ô nào chạm sàn/trần ở quý 18. Weighted không tốt hơn simple một cách nhất quán (trôi âm ở cả hai bộ dữ liệu). Không dùng bảng này để chọn θ hay benchmark.

### 6.4. Kết luận cho báo cáo: tác động chính sách có vững trước học thích nghi không?

**B−A và C−A vững, về định tính và gần như về định lượng.**
- Dấu: B−A và C−A âm ở mọi cấu hình, mọi bộ dữ liệu, và mọi seed (cả min–max đều âm), tức B và C không cao hơn A sau Q4/2026.
- Độ lớn B−A: 2023Q1 dao động −0.3987 đến −0.4079 so với −0.4005 khi TẮT (lệch tối đa 0.0074); 2026Q3 dao động −0.4067 đến −0.4155 so với −0.4023 (lệch tối đa 0.0132, khoảng 3%).
- Độ lớn C−A: 2023Q1 −0.4234 đến −0.4296 so với −0.4265 (lệch tối đa 0.0031); 2026Q3 −0.4319 đến −0.4468 so với −0.4283 (lệch tối đa 0.0185, khoảng 4%).
- So với biến thiên giữa seed: biên độ min–max của B−A theo seed là khoảng 0.06–0.09 điểm %. Đây chỉ là mức tham chiếu thô, vì độ lệch của trung bình không so được trực tiếp với biên độ từng seed.
- Chênh **ghép cặp từng seed** so với TẮT (10 seed; sai số chuẩn của trung bình ≈ sd/√10): trên 2023Q1, trung bình chênh của B−A nằm trong −0.0074…+0.0018 và của C−A trong −0.0031…+0.0031 (sai số chuẩn 0.002–0.004; phần lớn trong khoảng 2 sai số chuẩn, ngoại lệ gần nhất là B−A ở θ = 0.01: −0.0074 ± 0.0039); trên 2026Q3, B−A lệch −0.0043…−0.0131 và C−A lệch −0.0036…−0.0185 (sai số chuẩn 0.003–0.004). Ở 2026Q3 mọi độ lệch **cùng dấu âm** và nhiều giá trị vượt 2 sai số chuẩn (ví dụ C−A θ = 0.0025: −0.0185 ± 0.0038), nên relative làm tác động chính sách **mạnh lên một chút nhất quán** ở bộ này, không chỉ là nhiễu. Độ lệch ghép cặp lớn nhất của một seed là 0.045 điểm %.
- Trả lời câu hỏi trọng tâm: **B−A giữ nguyên dấu và gần như nguyên độ lớn qua mọi θ ∈ {0, 0.0025, 0.005, 0.01}**, kể cả khi biên trôi vượt ngưỡng ±0.1 (θ = 0 ở 2023Q1) hoặc khi dùng benchmark weighted.

Hạn chế khi diễn giải: đây là kiểm tra độ vững **trong mẫu của mô hình minh họa**, không phải ước lượng tác động chính sách thực tế. Vững trước quy tắc học này không có nghĩa vững trước mọi quy tắc học khác. Học làm đổi xác suất tuân thủ chỉ đạo vì `nim_proxy` phụ thuộc biên (reviewer đo thay đổi nhỏ với relative, lớn hơn với absolute), nên không loại hết được nhiễu lẫn. Quy tắc absolute không vững bằng: theo báo cáo reviewer Giai đoạn 5 (đo ngoài script, **chưa đưa vào repo nên chưa tái lập được từ đây**), B−A yếu đi khoảng 0.016 và xác suất tuân thủ giảm 0.05–0.07.

### 6.5. Lưu ý dữ liệu giả lập mặc định

Khi chạy với bộ giả lập mặc định của `ABMModel` (không nạp CSV), các ngân hàng giả lập có tăng trưởng đồng nhất nên luôn nằm trong vùng chết: relative cho kết quả **đúng bằng học TẮT**. Vì vậy dữ liệu giả lập **không kiểm chứng được cơ chế**; chỉ kết quả trên hai bộ dữ liệu thật 2023Q1 và 2026Q3 mới có ý nghĩa kiểm tra.

### 6.6. Phụ lục: biến thể không điều kiện nim (kết quả âm)

`scenarios_adaptive_relative_nonim.yaml` làm biên trôi **+0.237** điểm % sau 18 quý ở kịch bản A (bộ 2023Q1; +0.18 ở 2026Q3), đẩy `loan_rate` của A lên khoảng +0.31 điểm %. Lặp lại trên cả hai bộ dữ liệu nên là lỗi cơ chế, không phải dữ liệu. Test trôi của biến thể này được đánh dấu `xfail(strict=True)` kèm lý do để không ai chỉnh tham số cho "đẹp"; không dùng trong phân tích chính.

### 6.7. Việc còn chờ nhóm quyết định

θ = 0.005 và bước đối xứng 0.05 (chưa hiệu chỉnh); `simple` hay `weighted`; có chấp nhận tín hiệu tổng-không cùng điều kiện nim như một thiết kế hay cần tín hiệu khác; trích dẫn SFI ở mục 3 cần nhóm xác nhận.
