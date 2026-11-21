
"""Phân tích nâng cao mô hình ABM ngân hàng.

A - Tính không đồng nhất giữa các ngân hàng
B - Cơ chế truyền dẫn chính sách
C - Độ nhạy và đối chiếu dữ liệu thực tế

Một bước mô phỏng tương ứng một quý.
Tên biến 'month' được giữ để tương thích model.py.
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..core.model import ABMModel
from .experiments import load_config
from ..utils.output_utils import create_run_folder
from .sensitivity_grid import make_sensitivity_grid


ROOT = Path(__file__).resolve().parents[2]


# =====================================================
# 0. CẤU HÌNH BIỂU ĐỒ TIẾNG VIỆT
# =====================================================

plt.rcParams["font.family"] = "Arial"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11
plt.rcParams["figure.dpi"] = 120

SCENARIO_NAMES = {
    "A": "A - Không can thiệp",
    "B": "B - Chỉ đạo giảm lãi suất",
    "C": "C - Chính sách kết hợp",
}

SCENARIO_COLORS = {
    "A": "#2563EB",
    "B": "#F59E0B",
    "C": "#16A34A",
}

GROUP_NAMES = {
    "quoc_doanh": "Ngân hàng quốc doanh",
    "co_phan_lon": "Ngân hàng cổ phần lớn",
    "co_phan_nho": "Ngân hàng cổ phần nhỏ",
    "chua_phan_nhom": "Chưa phân nhóm",
}

PARAMETER_NAMES = {
    "pass_through": "Hệ số chuyển dịch chi phí vốn",
    "depositor_sensitivity": "Độ nhạy người gửi tiền",
    "policy_pressure": "Mức áp lực chính sách",
}


# =====================================================
# 1. CHẠY MÔ HÌNH VÀ THU THẬP DỮ LIỆU
# =====================================================

def run_panel(
    cfg,
    scenarios=("A", "B", "C"),
    n_runs=None,
    banks=None,
    params=None,
):
    p = dict(cfg["parameters"])

    if params:
        p.update(params)

    n = int(
        n_runs if n_runs is not None
        else cfg["n_runs"]
    )

    if n < 1:
        raise ValueError("Số lần chạy phải >= 1")

    bank_rows = (
        pd.read_csv(banks).to_dict("records")
        if banks else None
    )

    panels = []
    macros = []

    for scenario in scenarios:

        for i in range(n):

            seed = int(cfg["base_seed"]) + i

            model = ABMModel(
                scenario=scenario,
                n_months=int(cfg["n_months"]),
                seed=seed,
                parameters=p,
                initial_banks=bank_rows,
            )

            macro = model.run().copy()
            macro["run_id"] = i

            macros.append(macro)

            panel = pd.DataFrame(
                model.bank_history
            )

            panel["run_id"] = i
            panel["seed"] = seed
            panel["scenario"] = scenario

            panels.append(panel)

    return (
        pd.concat(panels, ignore_index=True),
        pd.concat(macros, ignore_index=True),
    )


# =====================================================
# 2. THỐNG KÊ THEO NHÓM NGÂN HÀNG
# =====================================================

def weighted_stats(g):

    loans = g["loans"].sum()
    deposits = g["deposits"].sum()

    active = bool(g["policy_active"].any())

    return pd.Series({
        "loan_rate": (
            (g["loan_rate"] * g["loans"]).sum() / loans
            if loans > 0 else np.nan
        ),

        "deposit_rate": (
            (g["deposit_rate"] * g["deposits"]).sum()
            / deposits
        ),

        "ldr": loans / deposits,

        "nim_proxy": (
            (g["nim_proxy"] * g["loans"]).sum() / loans
            if loans > 0 else np.nan
        ),

        "compliance_rate": (
            g["policy_complied"].mean()
            if active else np.nan
        ),

        "avg_policy_probability": (
            g["policy_probability"].mean()
            if active else np.nan
        ),

        "avg_direct_cut": g["policy_cut"].mean(),
    })


# =====================================================
# 3. VẼ BIỂU ĐỒ A, B, C
# =====================================================

def charts(
    bank_panel,
    macro,
    sensitivity,
    output,
    policy_month,
):

    # -------------------------------------------------
    # A. TÍNH KHÔNG ĐỒNG NHẤT GIỮA CÁC NGÂN HÀNG
    # -------------------------------------------------

    groups = (
        bank_panel.groupby(
            ["scenario", "run_id", "month", "group"]
        )
        .apply(
            weighted_stats,
            include_groups=False
        )
        .reset_index()
    )

    cols = [
        "loan_rate",
        "deposit_rate",
        "ldr",
        "nim_proxy",
    ]

    group_mean = (
        groups.groupby(
            ["scenario", "month", "group"],
            as_index=False,
        )[cols]
        .mean()
    )

    group_mean.to_csv(
        output / "A_nhom_ngan_hang.csv",
        index=False,
        encoding="utf-8-sig",
    )

    fig, ax = plt.subplots(figsize=(11, 6))

    data_B = group_mean[
        group_mean["scenario"] == "B"
    ]

    for name, part in data_B.groupby("group"):

        part = part.sort_values("month")

        ax.plot(
            part["month"],
            part["loan_rate"],
            label=GROUP_NAMES.get(name, str(name)),
            linewidth=2.3,
        )

    ax.axvline(
        policy_month + 1,
        linestyle="--",
        color="gray",
        linewidth=1.5,
        label="Bắt đầu can thiệp: Q4/2026",
    )

    ax.set(
        xlabel="Bước mô phỏng theo quý (Bước 1 = Q2/2023)",
        ylabel="Lãi suất cho vay (%/năm)",
        title=(
            "A - SỰ KHÁC BIỆT LÃI SUẤT CHO VAY "
            "GIỮA CÁC NHÓM NGÂN HÀNG\n"
            "(Kịch bản B - Chỉ đạo giảm lãi suất)"
        ),
    )

    ax.grid(alpha=0.2)
    ax.legend()

    fig.tight_layout()

    fig.savefig(
        output / "A_loan_rate_nhom.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    # -------------------------------------------------
    # B. PHÂN TÍCH TRUYỀN DẪN CHÍNH SÁCH
    # -------------------------------------------------

    paired = macro.pivot(
        index=["run_id", "month"],
        columns="scenario",
        values="loan_rate",
    ).reset_index()

    if not all(
        s in paired for s in ("A", "B", "C")
    ):
        raise ValueError(
            "Phải có đủ ba kịch bản A/B/C"
        )

    for name, left, right in [
        ("B_minus_A", "B", "A"),
        ("C_minus_A", "C", "A"),
        ("C_minus_B", "C", "B"),
    ]:
        paired[name] = (
            paired[left] - paired[right]
        )

    paired.to_csv(
        output / "B_chuyen_dan_tung_lan_chay.csv",
        index=False,
        encoding="utf-8-sig",
    )

    diff_cols = [
        "B_minus_A",
        "C_minus_A",
        "C_minus_B",
    ]

    avg = (
        paired.groupby(
            "month",
            as_index=False
        )[diff_cols]
        .mean()
    )

    avg.to_csv(
        output / "B_chuyen_dan_trung_binh.csv",
        index=False,
        encoding="utf-8-sig",
    )

    labels = {
        "B_minus_A": "Chỉ đạo giảm so với không can thiệp",
        "C_minus_A": "Chính sách kết hợp so với không can thiệp",
        "C_minus_B": "Chính sách kết hợp so với chỉ đạo giảm",
    }

    colors = {
        "B_minus_A": "#2563EB",
        "C_minus_A": "#16A34A",
        "C_minus_B": "#F59E0B",
    }

    fig, ax = plt.subplots(figsize=(11, 6))

    for col in diff_cols:

        ax.plot(
            avg["month"],
            avg[col],
            label=labels[col],
            color=colors[col],
            linewidth=2.3,
        )

    ax.axhline(
        0,
        color="gray",
        linewidth=0.8
    )

    ax.axvline(
        policy_month + 1,
        linestyle="--",
        color="gray",
        linewidth=1.5,
        label="Bắt đầu can thiệp: Q4/2026",
    )

    ax.set(
        xlabel="Bước mô phỏng theo quý (Bước 1 = Q2/2023)",
        ylabel=(
            "Chênh lệch lãi suất cho vay "
            "(điểm phần trăm)"
        ),
        title=(
            "B - PHÂN TÍCH TRUYỀN DẪN "
            "CHÍNH SÁCH GIẢM LÃI SUẤT"
        ),
    )

    ax.grid(alpha=0.2)
    ax.legend(fontsize=9)

    fig.tight_layout()

    fig.savefig(
        output / "B_chuyen_dan_chinh_sach.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    # Theo dõi mức tuân thủ chính sách

    compliance = (
        bank_panel[
            bank_panel["policy_active"]
        ]
        .groupby(
            ["scenario", "month"],
            as_index=False,
        )
        .agg(
            compliance_rate=(
                "policy_complied", "mean"
            ),

            mean_probability=(
                "policy_probability", "mean"
            ),

            mean_direct_cut=(
                "policy_cut", "mean"
            ),
        )
    )

    compliance.to_csv(
        output / "B_tuan_thu_chinh_sach.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # -------------------------------------------------
    # C. PHÂN TÍCH ĐỘ NHẠY CỦA CÁC THAM SỐ
    # -------------------------------------------------

    fig, axes = plt.subplots(
        1, 3,
        figsize=(16, 5)
    )

    for ax, (par, g) in zip(
        axes,
        sensitivity.groupby(
            "parameter",
            sort=False
        ),
    ):

        for scenario, sub in g.groupby("scenario"):

            sub = sub.sort_values("value")

            ax.plot(
                sub["value"],
                sub["mean_final_loan_rate"],
                marker="o",
                linewidth=2,
                color=SCENARIO_COLORS.get(scenario),
                label=SCENARIO_NAMES.get(
                    scenario,
                    scenario
                ),
            )

        ax.set(
            xlabel=PARAMETER_NAMES.get(par, par),
            ylabel="Lãi suất cho vay cuối kỳ (%/năm)",
        )

        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)

    fig.suptitle(
        "C - PHÂN TÍCH ĐỘ NHẠY "
        "CỦA CÁC THAM SỐ MÔ HÌNH",
        fontsize=15,
        fontweight="bold",
    )

    fig.tight_layout()

    fig.savefig(
        output / "C_do_nhay.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    return group_mean, compliance


# =====================================================
# 4. PHÂN TÍCH ĐỘ NHẠY
# =====================================================

def sensitivity_table(
    cfg,
    banks=None,
    n_runs=20,
):

    # Thấp / giá trị Huy nhập trong YAML / cao.
    # Đây là kịch bản độ nhạy, không phải khoảng tin cậy.
    grid = make_sensitivity_grid(cfg)

    rows = []

    for param, values in grid.items():

        for value in values:

            _, macro = run_panel(
                cfg,
                n_runs=n_runs,
                banks=banks,
                params={param: value},
            )

            last = (
                macro.sort_values("month")
                .groupby(
                    ["scenario", "run_id"]
                )
                .tail(1)
            )

            for sc, part in last.groupby("scenario"):

                rows.append({
                    "parameter": param,
                    "value": value,
                    "scenario": sc,
                    "n_runs": len(part),
                    "mean_final_loan_rate": (
                        part["loan_rate"].mean()
                    ),
                    "p05": (
                        part["loan_rate"].quantile(0.05)
                    ),
                    "p95": (
                        part["loan_rate"].quantile(0.95)
                    ),
                })

    return pd.DataFrame(rows)


# =====================================================
# 5. CHUẨN BỊ LÃI SUẤT THỰC TẾ TỪ PANEL
# =====================================================

def prepare_actual_from_panel(
    panel_path,
    output,
    initial_period="2023Q1",
    expected_banks=None,
):

    """Tính lãi suất cho vay bình quân gia quyền."""

    df = pd.read_csv(
        panel_path,
        encoding="utf-8-sig",
    )

    needed = {
        "bank_id",
        "period",
        "loans",
        "loan_rate_pct",
    }

    missing = needed - set(df.columns)

    if missing:
        raise ValueError(
            f"Panel thiếu cột: {sorted(missing)}"
        )

    df = df[list(needed)].copy()

    df["period"] = pd.PeriodIndex(
        df["period"].astype(str),
        freq="Q",
    )

    for col in ("loans", "loan_rate_pct"):
        df[col] = pd.to_numeric(
            df[col],
            errors="raise",
        )

    if (
        df.isna().any().any()
        or df.duplicated(
            ["bank_id", "period"]
        ).any()
    ):
        raise ValueError(
            "Panel có giá trị thiếu hoặc trùng ngân hàng-quý"
        )

    if (
        (df["loans"] <= 0).any()
        or not df["loan_rate_pct"].between(0, 100).all()
    ):
        raise ValueError(
            "Dư nợ hoặc lãi suất không hợp lệ"
        )

    start = pd.Period(
        initial_period,
        freq="Q",
    )

    if expected_banks is None:

        banks = set(
            df.loc[
                df["period"] == start,
                "bank_id"
            ]
        )

    else:

        banks = set(expected_banks)

        present = set(
            df.loc[
                df["period"] == start,
                "bank_id"
            ]
        )

        if banks != present:
            raise ValueError(
                "Danh sách ngân hàng khởi tạo không khớp"
            )

    if not banks:
        raise ValueError(
            "Không tìm thấy ngân hàng ở quý khởi tạo"
        )

    df = df[
        (df["bank_id"].isin(banks))
        & (df["period"] > start)
    ].copy()

    counts = (
        df.groupby("period")["bank_id"].nunique()
    )

    if (
        counts.empty
        or (counts != len(banks)).any()
    ):
        raise ValueError(
            "Thiếu ngân hàng trong chuỗi lịch sử"
        )

    df["weighted"] = (
        df["loans"] * df["loan_rate_pct"]
    )

    actual = (
        df.groupby(
            "period",
            as_index=False
        )
        .agg(
            total_loans=("loans", "sum"),
            weighted=("weighted", "sum"),
        )
    )

    actual["loan_rate"] = (
        actual["weighted"]
        / actual["total_loans"]
    )

    actual["month"] = [
        int(q.ordinal - start.ordinal)
        for q in actual["period"]
    ]

    if actual["month"].tolist() != list(
        range(1, len(actual) + 1)
    ):
        raise ValueError(
            "Chuỗi dữ liệu lịch sử bị thiếu quý"
        )

    actual["quarter"] = (
        actual["period"].astype(str)
    )

    actual = actual[
        ["month", "quarter", "loan_rate"]
    ]

    actual.to_csv(
        output / "C_lai_suat_thuc_te_tu_panel.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return actual


# =====================================================
# 6. ĐỐI CHIẾU THỰC TẾ VỚI MÔ PHỎNG
# =====================================================

def compare_actual(
    macro,
    actual_path,
    output,
    observed_scenario="A",
    policy_month=None,
):

    observed = pd.read_csv(actual_path)

    if not {
        "month",
        "loan_rate"
    }.issubset(observed.columns):
        raise ValueError(
            "Dữ liệu thực tế cần cột month,loan_rate"
        )

    if observed["month"].duplicated().any():
        raise ValueError(
            "Dữ liệu thực tế bị trùng bước quý"
        )

    actual = observed[
        ["month", "loan_rate"]
    ].copy()

    actual["month"] = pd.to_numeric(
        actual["month"],
        errors="raise",
    ).astype(int)

    actual["loan_rate"] = pd.to_numeric(
        actual["loan_rate"],
        errors="raise",
    )

    actual = actual.rename(
        columns={
            "loan_rate": "actual_loan_rate"
        }
    )

    if policy_month is not None:

        actual = actual[
            actual["month"] <= policy_month
        ].copy()

    sim = (
        macro[
            macro["scenario"] == observed_scenario
        ]
        .groupby(
            "month",
            as_index=False
        )["loan_rate"]
        .mean()
        .rename(
            columns={
                "loan_rate": "simulated_loan_rate"
            }
        )
    )

    comparison = (
        actual.merge(
            sim,
            on="month",
            how="inner",
        )
        .sort_values("month")
    )

    if comparison.empty:
        raise ValueError(
            "Không có quý thực tế trùng mô phỏng"
        )

    if len(comparison) != len(actual):
        raise ValueError(
            "Mô phỏng không bao phủ đủ quý lịch sử"
        )

    comparison["error"] = (
        comparison["simulated_loan_rate"]
        - comparison["actual_loan_rate"]
    )

    comparison.to_csv(
        output / "C_so_sanh_thuc_te.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metrics = pd.DataFrame([{
        "scenario": observed_scenario,
        "n_quarters": len(comparison),
        "MAE": (
            comparison["error"].abs().mean()
        ),
        "RMSE": np.sqrt(
            np.mean(comparison["error"] ** 2)
        ),
    }])

    metrics.to_csv(
        output / "C_sai_so.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # ------------------------------------------
    # BIỂU ĐỒ THỰC TẾ VÀ MÔ PHỎNG TIẾNG VIỆT
    # ------------------------------------------

    fig, ax = plt.subplots(
        figsize=(11, 6)
    )

    ax.plot(
        comparison["month"],
        comparison["actual_loan_rate"],
        marker="o",
        label="Lãi suất cho vay thực tế",
        color="#2563EB",
        linewidth=2.3,
    )

    ax.plot(
        comparison["month"],
        comparison["simulated_loan_rate"],
        marker="s",
        label=(
            "Lãi suất mô phỏng - "
            f"Kịch bản {observed_scenario}"
        ),
        color="#F97316",
        linewidth=2.3,
    )

    ax.set(
        xlabel="Bước mô phỏng theo quý (Bước 1 = Q2/2023)",
        ylabel="Lãi suất cho vay (%/năm)",
        title=(
            "C - SO SÁNH LÃI SUẤT CHO VAY "
            "THỰC TẾ VÀ MÔ PHỎNG\n"
            "(Đối chiếu lịch sử, chưa kiểm chứng "
            "tác động sau chính sách)"
        ),
    )

    ax.grid(alpha=0.2)
    ax.legend()

    fig.tight_layout()

    fig.savefig(
        output / "C_thuc_te_vs_mo_phong.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    return metrics


# =====================================================
# 7. KIỂM TRA 4.4 (ĐỘ TRỄ VÀ CHẨN ĐOÁN LỊCH SỬ)
# =====================================================

def check_funding_lag(banks_path, config):
    """Thử sốc lãi suất huy động giữa hai mô hình đối chứng giống hệt nhau."""
    rows = pd.read_csv(banks_path).to_dict('records')
    parameters = dict(config['parameters'])

    def build():
        return ABMModel(
            scenario='A', n_months=int(config['n_months']), seed=202611,
            parameters=dict(parameters), initial_banks=rows
        )

    baseline, shocked = build(), build()
    bank_0, bank_1 = baseline.banks[0], shocked.banks[0]
    # Hai ngân hàng có cùng trạng thái, chỉ ngân hàng thứ hai chịu cú sốc.
    shock_pp = 1.0  # tăng 1 điểm phần trăm lãi suất huy động
    bank_1.deposit_rate += shock_pp
    old_funding_0 = float(bank_0.lagged_funding_cost)
    old_funding_1 = float(bank_1.lagged_funding_cost)

    # Trong bước này, lãi suất cho vay sử dụng chi phí vốn TRỄ.
    bank_0.step()
    bank_1.step()
    first_diff = float(bank_1.loan_rate - bank_0.loan_rate)

    # Sang bước tiếp theo, thông tin chi phí vốn mới được ghi nhận.
    bank_0.finish_month()
    bank_1.finish_month()
    updated_funding_diff = float(
        bank_1.lagged_funding_cost - bank_0.lagged_funding_cost
    )
    bank_0.step()
    bank_1.step()
    second_diff = float(bank_1.loan_rate - bank_0.loan_rate)

    tests = {
        'chi_phi_von_tre_chua_doi_khi_nhan_soc': bool(
            np.isclose(old_funding_0, old_funding_1, atol=1e-10)
        ),
        'lai_suat_cho_vay_khong_doi_ngay_trong_buoc_dau': bool(
            np.isclose(first_diff, 0, atol=1e-10)
        ),
        'chi_phi_von_tre_phan_anh_soc_sau_chot_buoc': bool(
            updated_funding_diff > 0
        ),
        'lai_suat_cho_vay_tang_o_buoc_ke_tiep': bool(second_diff > 0),
    }
    return {
        'bank_id': str(bank_0.bank_id),
        'shock_deposit_rate_percentage_points': shock_pp,
        'loan_rate_difference_immediate_pp': first_diff,
        'funding_cost_difference_after_finish_pp': updated_funding_diff,
        'loan_rate_difference_next_step_pp': second_diff,
        'checks': tests,
        'all_passed': bool(all(tests.values())),
    }


def historical_diagnostics(folder, policy_month):
    comparison_path = folder / 'C_so_sanh_thuc_te.csv'
    policy_path = folder / 'B_chuyen_dan_trung_binh.csv'
    if not comparison_path.is_file():
        raise FileNotFoundError(
            f'Không thấy {comparison_path}. Hãy chạy advanced_analysis trước.'
        )

    df = pd.read_csv(comparison_path, encoding='utf-8-sig').sort_values('month')
    columns = {'month', 'actual_loan_rate', 'simulated_loan_rate'}
    missing = columns - set(df.columns)
    if missing:
        raise ValueError(f'CSV đối chiếu thiếu cột {sorted(missing)}')
    df = df[df['month'] <= int(policy_month)].copy()
    if df.empty:
        raise ValueError('Không có dữ liệu lịch sử trước chính sách')
    for col in ['month', 'actual_loan_rate', 'simulated_loan_rate']:
        df[col] = pd.to_numeric(df[col], errors='raise')
    if df[list(columns)].isna().any().any():
        raise ValueError('Có giá trị thiếu trong bảng đối chiếu')
    if df['month'].duplicated().any():
        raise ValueError('Trùng bước mô phỏng trong bảng đối chiếu')

    df['quarter'] = [
        str(pd.Period('2023Q1', freq='Q') + int(step))
        for step in df['month']
    ]
    df['error_pp'] = df['simulated_loan_rate'] - df['actual_loan_rate']
    df['absolute_error_pp'] = df['error_pp'].abs()
    df['actual_change_pp'] = df['actual_loan_rate'].diff()
    df['simulated_change_pp'] = df['simulated_loan_rate'].diff()
    df['same_direction'] = pd.Series(
        np.sign(df['actual_change_pp']) == np.sign(df['simulated_change_pp']),
        index=df.index, dtype='boolean'
    )
    df.loc[df['actual_change_pp'].isna(), 'same_direction'] = pd.NA
    df.to_csv(folder / 'D_chi_tiet_sai_lech_lich_su.csv', index=False, encoding='utf-8-sig')

    actual = df['actual_loan_rate'].to_numpy(float)
    simulated = df['simulated_loan_rate'].to_numpy(float)
    error = simulated - actual
    movements = df['same_direction'].dropna()
    min_idx = df['actual_loan_rate'].idxmin()
    max_idx = df['absolute_error_pp'].idxmax()

    metrics = {
        'n_quarters': int(len(df)),
        'from_quarter': str(df.iloc[0]['quarter']),
        'to_quarter': str(df.iloc[-1]['quarter']),
        'mae_percentage_points': float(np.mean(np.abs(error))),
        'rmse_percentage_points': float(np.sqrt(np.mean(error**2))),
        'bias_sim_minus_actual_percentage_points': float(np.mean(error)),
        'actual_minimum_quarter': str(df.loc[min_idx, 'quarter']),
        'actual_minimum_rate_pct': float(df.loc[min_idx, 'actual_loan_rate']),
        'largest_abs_error_quarter': str(df.loc[max_idx, 'quarter']),
        'largest_abs_error_pp': float(df.loc[max_idx, 'absolute_error_pp']),
        'direction_matches_n': int(movements.sum()),
        'direction_comparisons_n': int(len(movements)),
        'actual_range_pp': float(np.ptp(actual)),
        'simulated_range_pp': float(np.ptp(simulated)),
        'actual_first_pct': float(actual[0]),
        'actual_last_pct': float(actual[-1]),
        'simulated_first_pct': float(simulated[0]),
        'simulated_last_pct': float(simulated[-1]),
    }

    if policy_path.is_file():
        policy = pd.read_csv(policy_path).sort_values('month')
        need = {'month', 'B_minus_A', 'C_minus_A', 'C_minus_B'}
        if need.issubset(policy.columns):
            before = policy[policy['month'] <= int(policy_month)]
            after = policy[policy['month'] > int(policy_month)]
            metrics['scenarios_identical_before_policy'] = bool(
                (before[['B_minus_A', 'C_minus_A', 'C_minus_B']]
                 .abs().to_numpy() < 1e-10).all()
            ) if not before.empty else None
            metrics['post_policy_B_minus_A_mean_pp'] = (
                float(after['B_minus_A'].mean()) if not after.empty else None
            )
            metrics['post_policy_C_minus_A_mean_pp'] = (
                float(after['C_minus_A'].mean()) if not after.empty else None
            )

    return metrics



# =====================================================
# 8. BIỂU ĐỒ D — KIỂM TRA ĐỘ TRỄ VÀ SAI LỆCH
# =====================================================

def charts_validation_44(output, lag_result=None, history_result=None):
    """Vẽ biểu đồ chẩn đoán D từ kết quả đã tính; không chạy lại ABM."""
    output = Path(output)

    if lag_result is not None:
        # Chênh lệch giữa hai mô hình đối chứng chỉ tại một ngân hàng.
        # Bước đầu và bước kế tiếp được đo sau bank.step().
        values = [
            float(lag_result['loan_rate_difference_immediate_pp']),
            float(lag_result['loan_rate_difference_next_step_pp']),
        ]
        fig, ax = plt.subplots(figsize=(9, 5.5))
        bars = ax.bar(
            ['Bước đầu\n(chưa truyền dẫn)',
             'Bước kế tiếp\n(đã truyền dẫn)'],
            values, width=0.52, color=['#64748B', '#2563EB'],
        )
        ax.axhline(0, color='#475569', linewidth=0.8)
        ax.set(
            ylabel='Chênh lệch lãi suất cho vay (điểm phần trăm)',
            title='D1 - KIỂM TRA ĐỘ TRỄ TRUYỀN DẪN CHI PHÍ VỐN',
        )
        shock = float(lag_result['shock_deposit_rate_percentage_points'])
        ax.text(
            0.5, 0.97,
            f'Cú sốc: tăng {shock:g} điểm % lãi suất huy động của một ngân hàng',
            transform=ax.transAxes, ha='center', va='top', fontsize=10,
        )
        y_max = max(0.05, max(values) * 1.45)
        ax.set_ylim(min(-0.02, min(values) * 1.2), y_max)
        for bar, val in zip(bars, values):
            ax.annotate(
                f'{val:+.4f} điểm %',
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 6 if val >= 0 else -15),
                textcoords='offset points', ha='center', fontsize=10,
            )
        ax.grid(axis='y', alpha=0.2)
        fig.tight_layout()
        fig.savefig(
            output / 'D1_kiem_tra_do_tre.png', dpi=200,
            bbox_inches='tight',
        )
        plt.close(fig)

    history_path = output / 'D_chi_tiet_sai_lech_lich_su.csv'
    if history_result is not None and history_path.is_file():
        df = pd.read_csv(history_path, encoding='utf-8-sig').sort_values('month')
        if df.empty:
            return
        labels = df['quarter'].astype(str).tolist()
        x = np.arange(len(df))
        errors = df['error_pp'].to_numpy(dtype=float)
        colors = np.where(errors >= 0, '#F97316', '#2563EB')

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(x, errors, color=colors, width=0.72)
        ax.axhline(0, color='#475569', linewidth=1)
        bias = float(history_result['bias_sim_minus_actual_percentage_points'])
        ax.axhline(
            bias, color='#16A34A', linestyle='--', linewidth=1.6,
            label=f'Sai lệch bình quân có dấu: {bias:+.3f} điểm %',
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set(
            xlabel='Quý quan sát',
            ylabel='Sai lệch mô phỏng − thực tế (điểm phần trăm)',
            title='D2 - SAI LỆCH LÃI SUẤT CHO VAY THEO QUÝ',
        )
        ax.text(
            0.01, 0.97,
            'Cột dương: mô phỏng cao hơn thực tế; '
            'cột âm: mô phỏng thấp hơn thực tế',
            transform=ax.transAxes, ha='left', va='top', fontsize=9,
        )
        ax.grid(axis='y', alpha=0.2)
        ax.legend(loc='best')
        fig.tight_layout()
        fig.savefig(
            output / 'D2_sai_lech_lich_su_theo_quy.png', dpi=200,
            bbox_inches='tight',
        )
        plt.close(fig)

# =====================================================
# 7. CHƯƠNG TRÌNH CHÍNH
# =====================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default=str(ROOT / "configs/scenarios.yaml")
    )

    parser.add_argument(
        "--banks",
        help="CSV khởi tạo ngân hàng Q1/2023"
    )

    parser.add_argument(
        "--actual",
        help="CSV thực tế: month,loan_rate"
    )

    parser.add_argument(
        "--panel",
        default=str(
            ROOT / "data" / "clean"
            / "abm_panel_8nganhang_2023Q1_2026Q3.csv"
        ),
        help="Dữ liệu panel ngân hàng theo quý"
    )

    parser.add_argument(
        "--observed-scenario",
        choices=["A", "B", "C"],
        default="A"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=60
    )

    parser.add_argument(
        "--sensitivity-runs",
        type=int,
        default=20
    )

    args = parser.parse_args()

    cfg = load_config(args.config)

    output = create_run_folder(
        "PhanTichABC"
    )

    # 1. Chạy mô hình

    panel, macro = run_panel(
        cfg,
        n_runs=args.runs,
        banks=args.banks,
    )

    panel.to_csv(
        output / "A_du_lieu_tung_ngan_hang.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # 2. Phân tích độ nhạy

    sens = sensitivity_table(
        cfg,
        banks=args.banks,
        n_runs=args.sensitivity_runs,
    )

    sens.to_csv(
        output / "C_bang_do_nhay.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # 3. Vẽ biểu đồ A, B, C

    groups, compliance = charts(
        panel,
        macro,
        sens,
        output,
        int(
            cfg["parameters"].get(
                "policy_month", 12
            )
        ),
    )

    # 4. Tự đọc dữ liệu lịch sử

    if args.actual:

        actual_path = Path(args.actual)

    elif Path(args.panel).is_file():

        initial_banks = None

        if args.banks:

            initial_banks = (
                pd.read_csv(args.banks)["bank_id"]
                .astype(str)
                .tolist()
            )

        prepare_actual_from_panel(
            args.panel,
            output,
            expected_banks=initial_banks,
        )

        actual_path = (
            output / "C_lai_suat_thuc_te_tu_panel.csv"
        )

    else:

        actual_path = None

    # 5. Đối chiếu lịch sử

    if actual_path is not None:

        metrics = compare_actual(
            macro,
            actual_path,
            output,
            args.observed_scenario,
            policy_month=int(
                cfg["parameters"].get(
                    "policy_month", 12
                )
            ),
        )

        print(
            "\nKẾT QUẢ ĐỐI CHIẾU LỊCH SỬ:"
        )

        print(
            metrics.to_string(index=False)
        )

    else:

        print(
            "Không tìm thấy dữ liệu thực tế. "
            "Bỏ qua MAE/RMSE."
        )

    # 6. Kiểm tra nhiệm vụ 4.4 — không chạy lại A/B/C lần nữa.
    # Chỉ thực hiện 2 đối chứng ngắn cho cơ chế độ trễ
    # và đọc lại CSV do các phần A/B/C vừa xuất.
    lag_banks = Path(args.banks) if args.banks else (
        ROOT / "data" / "clean" / "abm_initial_8nganhang_2023Q1.csv"
    )
    lag_result = None
    history_result = None

    if lag_banks.is_file():
        lag_result = check_funding_lag(lag_banks, cfg)
        print("\nKIỂM TRA 4.4 — CƠ CHẾ ĐỘ TRỄ:")
        for name, passed in lag_result["checks"].items():
            print(("ĐẠT" if passed else "CHƯA ĐẠT") + ": " + name)
        print("Chênh lệch lãi suất ngay bước đầu:",
              round(lag_result["loan_rate_difference_immediate_pp"], 6), "điểm %")
        print("Chênh lệch lãi suất bước kế tiếp:",
              round(lag_result["loan_rate_difference_next_step_pp"], 6), "điểm %")
    else:
        print("\nBỏ qua kiểm tra độ trễ: chưa tìm thấy CSV ngân hàng khởi tạo.")

    if (output / "C_so_sanh_thuc_te.csv").is_file():
        history_result = historical_diagnostics(
            output, int(cfg["parameters"].get("policy_month", 12))
        )
        print("\nCHẨN ĐOÁN SAI LỆCH LỊCH SỬ:")
        for name, value in history_result.items():
            print(f"{name}: {value}")
    else:
        print("Bỏ qua chẩn đoán lịch sử: chưa có dữ liệu đối chiếu.")

    report_44 = {
        "lag_check": lag_result,
        "historical_diagnostics": history_result,
        "methodology_note": (
            "Kiểm tra độ trễ là kiểm tra cơ chế lập trình. Các chỉ tiêu MAE/RMSE "
            "lịch sử không phải đánh giá ngoài mẫu hay kiểm chứng tác động "
            "chính sách sau Q3/2026."
        ),
    }
    (output / "D_kiem_tra_nhiem_vu_4_4.json").write_text(
        json.dumps(report_44, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if lag_result is not None and not lag_result["all_passed"]:
        print("CẢNH BÁO: Có kiểm tra độ trễ chưa đạt; xem báo cáo 4.4.")

    charts_validation_44(output, lag_result, history_result)
    print("Đã xuất biểu đồ D1/D2 vào thư mục:", output)

    print(
        "\nĐã lưu toàn bộ phân tích vào:",
        output
    )

    print(
        "Dữ liệu ngân hàng:",
        len(panel),
        "dòng"
    )

    print(
        "Dữ liệu nhóm:",
        len(groups),
        "dòng"
    )

    print(
        "Dữ liệu tuân thủ:",
        len(compliance),
        "dòng"
    )


if __name__ == "__main__":
    main()
