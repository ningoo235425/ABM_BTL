"""So sánh kết quả mô hình với golden (tạo từ code gốc). Sai số tuyệt đối <= 1e-9."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.core.model import ABMModel

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden"
SEEDS = (202611, 202612, 202613)


def load_config():
    with open(ROOT / "configs/scenarios.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_model(scenario, seed, config=None):
    cfg = config or load_config()
    rows = pd.read_csv(
        ROOT / "data/clean/abm_initial_8nganhang_2023Q1.csv"
    ).to_dict("records")
    model = ABMModel(
        scenario, cfg["n_months"], seed, dict(cfg["parameters"]), rows
    )
    model.run()
    return pd.DataFrame(model.history), pd.DataFrame(model.bank_history)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("scenario", "ABC")
def test_golden(scenario, seed):
    history, bank_history = run_model(scenario, seed)
    for name, frame in (("history", history), ("bank_history", bank_history)):
        # round_trip: đọc lại đúng từng bit, tránh sai số parse với số lớn (~1e8)
        expected = pd.read_csv(
            GOLDEN / f"{name}_{scenario}_{seed}.csv", float_precision="round_trip"
        )
        # Chỉ so các cột có trong golden (cột mới được phép thêm vào cuối)
        pd.testing.assert_frame_equal(
            frame[list(expected.columns)],
            expected,
            check_exact=False,
            atol=1e-9,
            rtol=0,
        )
