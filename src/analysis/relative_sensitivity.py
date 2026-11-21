"""Chẩn đoán độ nhạy của quy tắc học relative theo θ và benchmark.

KHÔNG dùng để chọn tham số. Chỉ trả lời: B-A, C-A có ổn định khi θ/benchmark đổi không.
Chạy: python -m src.analysis.relative_sensitivity [--seeds 10]
Kết quả: outputs/relative_sensitivity.csv và bảng in ra màn hình.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ..core.model import ABMModel
from .experiments import load_config

ROOT = Path(__file__).resolve().parents[2]
DATASETS = {
    "2023Q1": ROOT / "data/clean/abm_initial_8nganhang_2023Q1.csv",
    "2026Q3": ROOT / "data/clean/abm_initial_8nganhang_2026Q3.csv",
}
THETAS = (0.0, 0.0025, 0.005, 0.01)
REL_CONFIG = ROOT / "configs/scenarios_adaptive_relative.yaml"


def run(cfg, params, rows, scenario, seed):
    model = ABMModel(scenario, int(cfg["n_months"]), seed, params, rows)
    model.run()
    return pd.DataFrame(model.history), pd.DataFrame(model.bank_history)


def evaluate(label, cfg, params, rows, seeds):
    """Một dòng chỉ số cho một cấu hình, trên tất cả seed."""
    pm = int(params["policy_month"])
    n = int(cfg["n_months"])
    lo, hi = params["margin_min"], params["margin_max"]
    init = ABMModel("A", n, seeds[0], params, rows).banks
    start = np.mean([b.target_margin for b in init])
    drift, floor, ceil, ba, ca = [], [], [], [], []
    for seed in seeds:
        res = {}
        for sc in "ABC":
            hist, bank = run(cfg, params, rows, sc, seed)
            res[sc] = (hist, bank)
        hist_a, bank_a = res["A"]
        last = bank_a[bank_a.month == n]
        drift.append(last.target_margin.mean() - start)
        floor.append((last.target_margin <= lo + 1e-9).mean())
        ceil.append((last.target_margin >= hi - 1e-9).mean())
        def post(sc):
            h = res[sc][0]
            return h[h.month > pm].loan_rate.mean()

        ba.append(post("B") - post("A"))
        ca.append(post("C") - post("A"))
    return {
        "bo_du_lieu": label[0], "cau_hinh": label[1],
        "troi_bien_q18": np.mean(drift),
        "cham_san_q18": np.mean(floor), "cham_tran_q18": np.mean(ceil),
        "B-A_tb": np.mean(ba), "B-A_min": np.min(ba), "B-A_max": np.max(ba),
        "C-A_tb": np.mean(ca), "C-A_min": np.min(ca), "C-A_max": np.max(ca),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "outputs/relative_sensitivity.csv"))
    args = ap.parse_args()

    cfg = load_config(REL_CONFIG)
    base = dict(cfg["parameters"])
    seeds = [202611 + i for i in range(args.seeds)]
    rows_out = []
    for dname, path in DATASETS.items():
        rows = pd.read_csv(path).to_dict("records")
        off = dict(base, adaptive_learning=False)
        rows_out.append(evaluate((dname, "TAT"), cfg, off, rows, seeds))
        for th in THETAS:
            p = dict(base, learning_deadband=th)
            rows_out.append(evaluate((dname, f"rel theta={th}"), cfg, p, rows, seeds))
        p = dict(base, learning_deadband=0.005, learning_benchmark="weighted")
        rows_out.append(evaluate((dname, "rel weighted theta=0.005"), cfg, p, rows, seeds))
    df = pd.DataFrame(rows_out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
