
"""Chạy lặp kịch bản ABM và xuất kết quả bằng tiếng Việt."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..core.model import ABMModel, HAS_MESA
from ..utils.output_utils import create_run_folder
from .sensitivity_grid import make_sensitivity_grid


ROOT = Path(__file__).resolve().parents[2]


def _deep_merge(base, override):
    """Trộn đệ quy: khóa trong override thay thế khóa cùng tên trong base."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path=None):
    """Nạp configs/scenarios.yaml, rồi trộn file ghi đè (nếu có) lên trên.

    File ghi đè chỉ cần chứa các khóa khác scenarios.yaml.
    """
    base_path = ROOT / "configs/scenarios.yaml"
    with open(base_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if path and Path(path).resolve() != base_path.resolve():
        with open(path, encoding="utf-8") as f:
            config = _deep_merge(config, yaml.safe_load(f) or {})
    return config


# ==================================================
# 1. CHẠY CÁC KỊCH BẢN A, B, C
# ==================================================

def simulate_all(config, outdir=None, real_data_csv=None):

    out = Path(outdir or ROOT / "outputs")
    out.mkdir(parents=True, exist_ok=True)

    params = dict(config["parameters"])
    n_runs = int(config["n_runs"])

    records = []
    all_runs = []

    bank_rows = None

    if real_data_csv:
        bank_rows = pd.read_csv(
            real_data_csv
        ).to_dict("records")

    for scenario in config["scenarios"]:

        runs = []

        for run_id in range(n_runs):

            seed = int(config["base_seed"]) + run_id

            model = ABMModel(
                scenario,
                config["n_months"],
                seed,
                params,
                bank_rows
            )

            frame = model.run()
            frame["run_id"] = run_id

            runs.append(frame)

        scenario_frame = pd.concat(
            runs,
            ignore_index=True
        )

        scenario_frame.to_csv(
            out / f"runs_{scenario}.csv",
            index=False,
            encoding="utf-8-sig"
        )

        all_runs.append(scenario_frame)

        for run_id, chunk in scenario_frame.groupby("run_id"):

            final = chunk.iloc[-1]

            records.append({
                "scenario": scenario,
                "run_id": run_id,
                "seed": int(final.seed),
                "final_loan_rate": float(final.loan_rate),
                "final_deposit_rate": float(final.deposit_rate),
                "mean_loan_rate": float(chunk.loan_rate.mean()),
                "final_ldr": float(final.loan_deposit_ratio)
            })

    results = pd.DataFrame(records)

    summary = results.groupby("scenario").agg(
        n_runs=("run_id", "size"),
        final_loan_rate_mean=("final_loan_rate", "mean"),
        final_loan_rate_p05=(
            "final_loan_rate",
            lambda x: np.quantile(x, 0.05)
        ),
        final_loan_rate_p95=(
            "final_loan_rate",
            lambda x: np.quantile(x, 0.95)
        ),
        final_deposit_rate_mean=(
            "final_deposit_rate", "mean"
        ),
        final_ldr_mean=(
            "final_ldr", "mean"
        )
    ).reset_index()

    summary.to_csv(
        out / "bang_ket_qua.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return (
        pd.concat(all_runs, ignore_index=True),
        summary
    )


# ==================================================
# 2. PHÂN TÍCH ĐỘ NHẠY
# ==================================================

def sensitivity(config, outdir=None, real_data_csv=None):

    out = Path(outdir or ROOT / "outputs")

    bank_rows = (
        pd.read_csv(real_data_csv).to_dict("records")
        if real_data_csv else None
    )

    base = dict(config["parameters"])

    # Ba mức thấp/cơ sở/cao tự xoay quanh YAML; không viết cứng.
    vals = make_sensitivity_grid(config)

    results = []

    for par, candidates in vals.items():

        for value in candidates:

            p = dict(base)
            p[par] = value

            for sc in ("A", "B", "C"):

                for i in range(
                    min(int(config["n_runs"]), 30)
                ):

                    seed = int(config["base_seed"]) + i

                    frame = ABMModel(
                        sc,
                        config["n_months"],
                        seed,
                        p,
                        bank_rows
                    ).run()

                    results.append({
                        "parameter": par,
                        "value": value,
                        "scenario": sc,
                        "seed": seed,
                        "final_loan_rate": (
                            frame.loan_rate.iloc[-1]
                        )
                    })

    df = pd.DataFrame(results)

    df.to_csv(
        out / "sensitivity.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return df


# ==================================================
# 3. TẠO BIỂU ĐỒ TIẾNG VIỆT
# ==================================================

def create_charts(all_runs, outdir=None, actual_csv=None):

    import matplotlib
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    # Font hỗ trợ tiếng Việt trên Windows
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11

    out = Path(outdir or ROOT / "outputs")

    scenario_names = {
        "A": "A - Không can thiệp",
        "B": "B - Chỉ đạo giảm lãi suất",
        "C": "C - Chính sách kết hợp"
    }

    scenario_colors = {
        "A": "#2563EB",
        "B": "#F59E0B",
        "C": "#16A34A"
    }

    # ------------------------------------------
    # BIỂU ĐỒ 1: SO SÁNH BA KỊCH BẢN CHÍNH SÁCH
    # ------------------------------------------

    fig, ax = plt.subplots(figsize=(11, 6))

    for sc, group in all_runs.groupby("scenario"):

        ag = group.groupby("month")["loan_rate"].agg(
            mean="mean",
            p05=lambda x: x.quantile(0.05),
            p95=lambda x: x.quantile(0.95)
        )

        x = ag.index.to_numpy(dtype=float)

        color = scenario_colors.get(sc, "#64748B")

        ax.plot(
            x,
            ag["mean"].to_numpy(dtype=float),
            label=scenario_names.get(sc, sc),
            color=color,
            linewidth=2.3
        )

        ax.fill_between(
            x,
            ag.p05.to_numpy(dtype=float),
            ag.p95.to_numpy(dtype=float),
            color=color,
            alpha=0.15
        )

    ax.axvline(
        15,
        color="#64748B",
        linestyle="--",
        linewidth=1.5,
        label="Bắt đầu chính sách: Q4/2026"
    )

    ax.set(
        xlabel="Bước mô phỏng theo quý (Bước 1 = Q2/2023)",
        ylabel="Lãi suất cho vay (%/năm)",
        title=(
            "SO SÁNH LÃI SUẤT CHO VAY "
            "GIỮA BA KỊCH BẢN CHÍNH SÁCH"
        )
    )

    ax.grid(alpha=0.2)

    ax.legend(
        loc="best",
        fontsize=10
    )

    fig.tight_layout()

    fig.savefig(
        out / "fig_scenarios.png",
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(fig)

    # ------------------------------------------
    # BIỂU ĐỒ 2: SO SÁNH THỰC TẾ VÀ MÔ PHỎNG
    # ------------------------------------------

    if actual_csv:

        actual = pd.read_csv(actual_csv)

        if not {"month", "loan_rate"}.issubset(
            actual.columns
        ):
            raise ValueError(
                "CSV thực tế phải có cột month,loan_rate"
            )

        baseline = (
            all_runs[all_runs.scenario == "A"]
            .groupby("month")["loan_rate"]
            .mean()
            .reset_index()
        )

        comparison = actual[
            ["month", "loan_rate"]
        ].merge(
            baseline,
            on="month",
            how="inner",
            suffixes=("_actual", "_simulated")
        )

        if comparison.empty:
            raise ValueError(
                "Không có quý trùng nhau giữa "
                "dữ liệu thực tế và mô phỏng"
            )

        fig, ax = plt.subplots(figsize=(11, 6))

        ax.plot(
            comparison.month,
            comparison.loan_rate_actual,
            label="Lãi suất thực tế",
            color="#2563EB",
            marker="o",
            linewidth=2.2
        )

        ax.plot(
            comparison.month,
            comparison.loan_rate_simulated,
            label="Lãi suất mô phỏng - Kịch bản A",
            color="#F97316",
            marker="s",
            linewidth=2.2
        )

        ax.set(
            xlabel="Bước mô phỏng theo quý (Bước 1 = Q2/2023)",
            ylabel="Lãi suất cho vay (%/năm)",
            title=(
                "SO SÁNH LÃI SUẤT CHO VAY "
                "THỰC TẾ VÀ MÔ PHỎNG\n"
                "(Đối chiếu lịch sử, chưa kiểm chứng "
                "tác động sau chính sách)"
            )
        )

        ax.grid(alpha=0.2)
        ax.legend()

        fig.tight_layout()

        fig.savefig(
            out / "fig_calibration.png",
            dpi=200,
            bbox_inches="tight"
        )

        plt.close(fig)


# ==================================================
# 4. CHƯƠNG TRÌNH CHÍNH
# ==================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default=str(ROOT / "configs/scenarios.yaml")
    )

    parser.add_argument(
        "--banks",
        help="CSV dữ liệu ngân hàng đã làm sạch"
    )

    parser.add_argument(
        "--actual",
        help="CSV lãi suất thực tế: month,loan_rate"
    )

    parser.add_argument(
        "--runs",
        type=int,
        help="Ghi đè số lần chạy mô phỏng"
    )

    args = parser.parse_args()

    config = load_config(args.config)

    if args.runs is not None:
        config["n_runs"] = args.runs

    # Tạo thư mục riêng cho mỗi lần chạy
    out = create_run_folder("KichBan")

    all_runs, summary = simulate_all(
        config,
        out,
        args.banks
    )

    sensitivity(
        config,
        out,
        args.banks
    )

    create_charts(
        all_runs,
        out,
        args.actual
    )

    metadata = {
        "data_status": (
            "DEMONSTRATION - synthetic bank initialization"
            if not args.banks
            else "USER PROVIDED - verify source"
        ),
        "config": config,
        "mesa_available": HAS_MESA,
        "actual_comparison_available": bool(args.actual),
        "note": (
            "Các tham số hiện tại là giả định minh họa, "
            "chưa được hiệu chỉnh từ dữ liệu thực tế."
        )
    }

    (out / "run_metadata.json").write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\nĐã xuất kết quả vào:", out)

    print("\nBẢNG KẾT QUẢ MÔ PHỎNG:")
    print(summary.to_string(index=False))

    if not args.actual:
        print(
            "\nChưa tạo fig_calibration.png "
            "vì chưa truyền chuỗi lãi suất thực tế."
        )


if __name__ == "__main__":
    main()
