
"""Mô hình ABM dùng Mesa 3.3.1, một bước = một quý.

Tên kỹ thuật month/n_months được giữ để không phá API và CSV cũ.
Các tham số chưa hiệu chỉnh, các tốc độ tăng trưởng là giả định mỗi quý.
"""

import pandas as pd
from mesa import Model

from ..agents.bank import Bank
from ..agents.regulator import Regulator
from ..agents.depositors import DepositorBlock
from ..agents.borrowers import BorrowerBlock


GROUPS = (
    "quoc_doanh",
    "co_phan_lon",
    "co_phan_nho",
)

HAS_MESA = True


class ABMModel(Model):
    def __init__(
        self,
        scenario="A",
        n_months=24,
        seed=42,
        parameters=None,
        initial_banks=None,
    ):
        super().__init__(seed=seed)

        if scenario not in ("A", "B", "C"):
            raise ValueError("Kịch bản phải là A, B hoặc C")

        self.scenario = scenario
        self.n_months = int(n_months)
        self.seed = int(seed)
        self.month = 0

        # Ky khoi tao tu du lieu BCTC
        self.initial_period = pd.Period(
            "2023Q1", freq="Q"
        )
        self.time_unit = "quarter"


        p = dict(parameters or {})

        self.pass_through = float(
            p.get("pass_through", 0.48)
        )
        self.policy_step = float(
            p.get("policy_step", 0.28)
        )
        self.policy_month = int(
            p.get("policy_month", 14)
        )
        self.deposit_competition = float(
            p.get("deposit_competition", 0.07)
        )
        self.deposit_cap_factor = float(
            p.get("deposit_cap_factor", 0.25)
        )
        self.max_loan_to_deposit = float(
            p.get("max_loan_to_deposit", 1.60)
        )

        # Hằng số hành vi trước đây cứng trong agent (giá trị giữ nguyên)
        self.base_deposit_rate_step = float(
            p.get("base_deposit_rate_step", 0.018)
        )
        self.loan_spread_add = float(
            p.get("loan_spread_add", 1.35)
        )

        # Học thích nghi (tùy chọn, mặc định TẮT để tái lập kết quả cũ)
        self.adaptive_learning = bool(
            p.get("adaptive_learning", False)
        )
        self.learning_up_step = float(
            p.get("learning_up_step", 0.05)
        )
        self.learning_down_step = float(
            p.get("learning_down_step", 0.10)
        )
        self.learning_growth_threshold = float(
            p.get("learning_growth_threshold", 0.006)
        )
        self.learning_nim_threshold = float(
            p.get("learning_nim_threshold", 5.5875)
        )
        # Quy tắc học "relative": so sánh với mốc bình quân hệ thống (mặc định TẮT)
        self.learning_rule = str(p.get("learning_rule", "absolute"))
        self.learning_deadband = float(
            p.get("learning_deadband", 0.005)
        )
        self.learning_benchmark = str(
            p.get("learning_benchmark", "simple")
        )
        self.learning_nim_condition = bool(
            p.get("learning_nim_condition", True)
        )
        self.margin_min = float(p.get("margin_min", 2.2))
        self.margin_max = float(p.get("margin_max", 4.2))

        if self.learning_rule not in ("absolute", "relative"):
            raise ValueError("learning_rule phải là absolute hoặc relative")
        if self.learning_benchmark not in ("simple", "weighted"):
            raise ValueError("learning_benchmark phải là simple hoặc weighted")
        if self.learning_deadband < 0:
            raise ValueError("learning_deadband phải không âm")
        self._learning_stats_cache = None

        if self.margin_min > self.margin_max:
            raise ValueError("margin_min không được lớn hơn margin_max")
        if self.learning_up_step < 0 or self.learning_down_step < 0:
            raise ValueError("Bước học phải không âm")

        if self.n_months <= 0:
            raise ValueError("n_months phải dương")

        if self.max_loan_to_deposit <= 0:
            raise ValueError(
                "Giới hạn kỹ thuật dư nợ/tiền gửi phải lớn hơn 0"
            )

        # Tạo agent NHNN
        self.regulator = Regulator(
            self,
            pressure=float(
                p.get("policy_pressure", 0.65)
            ),
            margin_floor=float(
                p.get("margin_floor", 2.2)
            ),
        )

        # Tạo agent người gửi tiền gộp
        self.depositor = DepositorBlock(
            self,
            sensitivity=float(
                p.get("depositor_sensitivity", 0.035)
            ),
        )

        # Tạo agent người vay gộp
        self.borrower = BorrowerBlock(
            self,
            elasticity=float(
                p.get("borrower_elasticity", 0.012)
            ),
            reference_rate=float(
                p.get("borrower_reference_rate", 9.5)
            ),
            base_growth=float(
                p.get("borrower_base_growth", 0.006)
            ),
        )

        # Tạo các agent ngân hàng
        self.banks = self._make_banks(initial_banks)

        self.market_rate = 0.0
        self.history = []
        self.bank_history = []
    def _make_banks(self, initial):
        """Khởi tạo ngân hàng từ dữ liệu hoặc bộ giả lập."""
        if initial is None:
            initial = []

            for i in range(9):
                deposits = 1000 + 140 * i

                initial.append({
                    "bank_id": f"DEMO_{i + 1:02d}",
                    "group": GROUPS[i // 3],
                    "deposits": deposits,
                    "loans": deposits * 0.82,
                    "deposit_rate": 5.0 + 0.12 * (i % 3),
                    "loan_rate": 9.2 + 0.15 * (i % 3),
                    "casa_ratio": 0.27 - 0.05 * (i // 3),
                })

        required = {
            "bank_id",
            "group",
            "deposits",
            "loans",
            "deposit_rate",
            "loan_rate",
        }

        banks = []

        for item in initial:
            if not required.issubset(item):
                missing = required - set(item)

                raise ValueError(
                    f"Thiếu cột ngân hàng: {missing}"
                )

            d = dict(item)

            if d["deposits"] <= 0 or d["loans"] < 0:
                raise ValueError(
                    "Dữ liệu số dư không hợp lệ"
                )

            bank = Bank(self, **d)

            # Chi phí vốn ban đầu
            bank.lagged_funding_cost = (
                bank.funding_cost
            )

            banks.append(bank)

        if not banks:
            raise ValueError(
                "Danh sách ngân hàng không được rỗng"
            )

        # Trạng thái đầu kỳ cho học thích nghi (không dùng số ngẫu nhiên)
        total_loans = sum(b.loans for b in banks)
        for bank in banks:
            bank.prev_loans = bank.loans
            bank.prev_loan_share = (
                bank.loans / total_loans if total_loans > 0 else 0.0
            )

        return banks

    def step(self):
        """Thực hiện một bước mô phỏng = một quý."""

        # 1. Lưu dữ liệu đầu kỳ
        rates_before = [
            bank.deposit_rate for bank in self.banks
        ]

        self.market_rate = (
            sum(rates_before) / len(rates_before)
        )

        old_deposits = sum(
            bank.deposits for bank in self.banks
        )

        old_loans = sum(
            bank.loans for bank in self.banks
        )

        # 2. Kích hoạt NHNN
        self.agents_by_type[Regulator].do("step")

        # 3. Kích hoạt ngân hàng
        self.agents_by_type[Bank].do("step")

        # 4. Kích hoạt người gửi tiền
        self.agents_by_type[DepositorBlock].do("step")

        # 5. Kích hoạt người vay
        self.agents_by_type[BorrowerBlock].do("step")

        # 6. Kiểm tra các ràng buộc
        for bank in self.banks:
            bank.finish_month()

            assert 0 <= bank.loan_rate <= 20
            assert 0 <= bank.deposit_rate <= 14

            assert bank.deposits > 0
            assert bank.loans >= 0

            assert (
                bank.loans
                <= bank.deposits
                * self.max_loan_to_deposit
                + 1e-9
            )

            assert 0 <= bank.casa_ratio <= 1
            assert 0 <= bank.npl_ratio <= 1

            # Ghi nhận trạng thái ngân hàng cuối quý
            self.bank_history.append({
                "month": self.month + 1,
                "bank_id": bank.bank_id,
                "group": bank.group,

                # Đặc điểm tài chính
                "casa_ratio": bank.casa_ratio,
                "deposits": bank.deposits,
                "loans": bank.loans,

                # Lãi suất và biên lãi
                "deposit_rate": bank.deposit_rate,
                "loan_rate": bank.loan_rate,
                "nim_proxy": bank.nim_proxy,

                # Thanh khoản
                "ldr": bank.loans / bank.deposits,

                # Thông tin chính sách
                "policy_active": (
                    self.regulator.policy_active
                ),
                "policy_probability": (
                    bank.policy_probability
                ),
                "policy_complied": (
                    bank.policy_complied
                ),
                "policy_cut": bank.policy_cut,

                # Biên mục tiêu áp dụng cho quý kế tiếp (cột mới)
                "target_margin": bank.target_margin,
            })

        # 7. Tổng hợp trạng thái toàn hệ thống
        new_deposits = sum(
            bank.deposits for bank in self.banks
        )

        new_loans = sum(
            bank.loans for bank in self.banks
        )

        weighted_deposit_rate = sum(
            bank.deposit_rate * bank.deposits
            for bank in self.banks
        ) / new_deposits

        weighted_loan_rate = sum(
            bank.loan_rate * bank.loans
            for bank in self.banks
        ) / new_loans

        weighted_nim_proxy = sum(
            bank.nim_proxy * bank.loans
            for bank in self.banks
        ) / new_loans

        # 8. Lưu kết quả theo quý
        self.history.append({
            "month": self.month + 1,
            "quarter": str(
                self.initial_period + self.month + 1
            ),
            "scenario": self.scenario,
            "seed": self.seed,
            "deposit_rate": weighted_deposit_rate,
            "loan_rate": weighted_loan_rate,
            "nim_proxy": weighted_nim_proxy,
            "credit_growth": (
                new_loans / old_loans - 1
            ),
            "deposit_growth": (
                new_deposits / old_deposits - 1
            ),
            "loan_deposit_ratio": (
                new_loans / new_deposits
            ),
            "total_loans": new_loans,
            "total_deposits": new_deposits,
        })

        self.month += 1

    def run(self):
        """Chạy mô phỏng đến hết số quý đã định."""
        for _ in range(self.n_months):
            self.step()

        return pd.DataFrame(self.history)

    @staticmethod
    def from_clean_csv(path, **kwargs):
        """Khởi tạo ngân hàng từ CSV dạng wide."""
        data = pd.read_csv(path)

        banks = data.to_dict("records")

        return ABMModel(
            initial_banks=banks,
            **kwargs
        )
