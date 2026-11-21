"""Kiểm thử học thích nghi của ngân hàng (target_margin)."""

import pandas as pd
import pytest
from pathlib import Path

from src.analysis.experiments import load_config as merged_config, _deep_merge
from src.core.model import ABMModel
from tests.test_golden import ROOT, GOLDEN, load_config, run_model

ADAPTIVE = ROOT / "configs/scenarios_adaptive.yaml"


RELATIVE = ROOT / "configs/scenarios_adaptive_relative.yaml"
RELATIVE_NONIM = ROOT / "configs/scenarios_adaptive_relative_nonim.yaml"


def adaptive_config():
    return merged_config(ADAPTIVE)


def make_model(**overrides):
    cfg = load_config()
    params = dict(cfg["parameters"])
    params["adaptive_learning"] = True
    params.update(overrides)
    rows = pd.read_csv(
        ROOT / "data/clean/abm_initial_8nganhang_2023Q1.csv"
    ).to_dict("records")
    return ABMModel("A", cfg["n_months"], 202611, params, rows)


def test_deep_merge_and_override_files():
    base = {"a": 1, "parameters": {"x": 1, "y": 2}}
    assert _deep_merge(base, {"parameters": {"y": 3}}) == {
        "a": 1, "parameters": {"x": 1, "y": 3}
    }
    assert base["parameters"]["y"] == 2  # không sửa bản gốc
    off = load_config()
    assert off["parameters"]["adaptive_learning"] is False
    assert off["parameters"]["learning_rule"] == "absolute"
    on = merged_config(ADAPTIVE)
    assert on["parameters"]["adaptive_learning"] is True
    assert on["parameters"]["learning_rule"] == "absolute"
    # Khóa không ghi đè phải giữ nguyên từ scenarios.yaml
    assert on["parameters"]["pass_through"] == off["parameters"]["pass_through"]
    assert on["n_runs"] == off["n_runs"]
    for path, nim in ((RELATIVE, True), (RELATIVE_NONIM, False)):
        rel = merged_config(path)["parameters"]
        assert rel["learning_rule"] == "relative"
        assert rel["learning_down_step"] == 0.05
        assert rel["learning_nim_condition"] is nim


def test_off_by_default_in_code():
    assert ABMModel(seed=1).adaptive_learning is False


def test_off_matches_golden_and_margin_constant():
    for scenario in "ABC":
        history, bank_history = run_model(scenario, 202611)
        expected = pd.read_csv(
            GOLDEN / f"bank_history_{scenario}_202611.csv",
            float_precision="round_trip",
        )
        pd.testing.assert_frame_equal(
            bank_history[list(expected.columns)], expected,
            check_exact=False, atol=1e-9, rtol=0,
        )
        assert "target_margin" in bank_history.columns
        assert (bank_history.target_margin == 3.2).all()


def test_old_columns_unchanged_order():
    _, bank_history = run_model("A", 202611)
    expected = pd.read_csv(GOLDEN / "bank_history_A_202611.csv")
    assert list(bank_history.columns[:-1]) == list(expected.columns)
    assert bank_history.columns[-1] == "target_margin"


def test_margin_falls_when_loan_share_falls():
    model = make_model()
    bank = model.banks[0]
    # Dư nợ không đổi, các ngân hàng khác tăng => thị phần dư nợ giảm
    for other in model.banks[1:]:
        other.loans *= 1.2
    before = bank.target_margin
    bank.finish_month()
    assert bank.target_margin == pytest.approx(
        before - model.learning_down_step
    )


def test_margin_rises_when_growing_and_nim_high():
    model = make_model(learning_nim_threshold=0.0)
    bank = model.banks[0]
    # Chỉ ngân hàng này tăng mạnh => thị phần tăng, tăng trưởng >= g*
    bank.loans *= 1.10
    before = bank.target_margin
    bank.finish_month()
    assert bank.target_margin == pytest.approx(
        before + model.learning_up_step
    )


def test_no_rise_when_nim_below_threshold():
    model = make_model(learning_nim_threshold=1e9)
    bank = model.banks[0]
    bank.loans *= 1.10
    before = bank.target_margin
    bank.finish_month()
    assert bank.target_margin == before


def test_only_decrease_when_both_signals():
    model = make_model(learning_nim_threshold=0.0)
    bank = model.banks[0]
    # Tăng trưởng 1% >= g* nhưng các ngân hàng khác tăng nhanh hơn => thị phần giảm
    bank.loans *= 1.01
    for other in model.banks[1:]:
        other.loans *= 1.30
    before = bank.target_margin
    bank.finish_month()
    assert bank.target_margin == pytest.approx(
        before - model.learning_down_step
    )


def test_margin_clipped_to_bounds():
    # Sàn
    model = make_model(learning_down_step=10.0)
    bank = model.banks[0]
    for other in model.banks[1:]:
        other.loans *= 1.2
    bank.finish_month()
    assert bank.target_margin == model.margin_min
    # Trần
    model = make_model(learning_up_step=10.0, learning_nim_threshold=0.0)
    bank = model.banks[0]
    bank.loans *= 1.10
    bank.finish_month()
    assert bank.target_margin == model.margin_max


@pytest.mark.parametrize("scenario", "ABC")
def test_margin_within_bounds_full_run(scenario):
    cfg = adaptive_config()
    _, bank_history = run_model(scenario, 202611, cfg)
    p = cfg["parameters"]
    assert bank_history.target_margin.between(
        p["margin_min"], p["margin_max"]
    ).all()


def test_learning_has_no_effect_before_policy_only_via_state():
    # Học không dùng số ngẫu nhiên: A/B/C vẫn trùng nhau trước thời điểm chính sách
    cfg = adaptive_config()
    pm = cfg["parameters"]["policy_month"]
    frames = {s: run_model(s, 202611, cfg)[0] for s in "ABC"}
    pre = lambda f: f[f.month <= pm][["loan_rate", "deposit_rate", "total_loans"]]
    pd.testing.assert_frame_equal(pre(frames["A"]), pre(frames["B"]))
    pd.testing.assert_frame_equal(pre(frames["A"]), pre(frames["C"]))


def test_invalid_margin_bounds():
    with pytest.raises(ValueError):
        make_model(margin_min=5.0, margin_max=4.0)


# ---------------- Quy tắc relative ----------------

def make_relative(**overrides):
    return make_model(learning_rule="relative", **overrides)


def test_relative_defaults_in_code():
    m = ABMModel(seed=1)
    assert m.learning_rule == "absolute"
    assert m.learning_deadband == 0.005
    assert m.learning_benchmark == "simple"
    assert m.learning_nim_condition is True


def test_relative_invalid_options():
    with pytest.raises(ValueError):
        make_model(learning_rule="khac")
    with pytest.raises(ValueError):
        make_model(learning_benchmark="khac")
    with pytest.raises(ValueError):
        make_model(learning_deadband=-0.1)


def test_relative_deadband_keeps_margin():
    model = make_relative()
    # Tất cả cùng tăng 1% => g_i = g_bar, nằm trong vùng chết
    for b in model.banks:
        b.loans *= 1.01
    before = [b.target_margin for b in model.banks]
    for b in model.banks:
        b.finish_month()
    assert [b.target_margin for b in model.banks] == before


def test_relative_falls_when_below_benchmark_by_more_than_deadband():
    model = make_relative()
    bank = model.banks[0]
    for other in model.banks[1:]:
        other.loans *= 1.05
    before = bank.target_margin
    for b in model.banks:
        b.finish_month()
    assert bank.target_margin == pytest.approx(before - model.learning_down_step)


def test_relative_rises_when_above_benchmark_and_nim_ok():
    model = make_relative()
    bank = model.banks[0]
    bank.loans *= 1.10
    # Bảo đảm nim của bank >= bình quân
    bank.loan_rate += 5.0
    before = bank.target_margin
    for b in model.banks:
        b.finish_month()
    assert bank.target_margin == pytest.approx(before + model.learning_up_step)


def test_relative_no_rise_when_nim_below_average():
    bank_idx = 0
    # Có điều kiện nim: không tăng
    model = make_relative()
    bank = model.banks[bank_idx]
    bank.loans *= 1.10
    bank.loan_rate -= 5.0
    before = bank.target_margin
    for b in model.banks:
        b.finish_month()
    assert bank.target_margin == before
    # Không điều kiện nim: vẫn tăng
    model = make_relative(learning_nim_condition=False)
    bank = model.banks[bank_idx]
    bank.loans *= 1.10
    bank.loan_rate -= 5.0
    before = bank.target_margin
    for b in model.banks:
        b.finish_month()
    assert bank.target_margin == pytest.approx(before + model.learning_up_step)


def test_relative_stats_computed_once_per_quarter():
    # Kết quả không phụ thuộc thứ tự cập nhật ngân hàng
    def run(order):
        model = make_relative(learning_nim_condition=False)
        for i, b in enumerate(model.banks):
            b.loans *= 1 + 0.01 * i
        for i in order:
            model.banks[i].finish_month()
        return [b.target_margin for b in model.banks]
    n = 8
    assert run(range(n)) == run(reversed(range(n)))


def test_relative_weighted_benchmark_runs():
    model = make_relative(learning_benchmark="weighted")
    model.banks[0].loans *= 1.10
    for b in model.banks:
        b.finish_month()
    assert all(
        model.margin_min <= b.target_margin <= model.margin_max
        for b in model.banks
    )


@pytest.mark.parametrize("path", [RELATIVE, RELATIVE_NONIM])
@pytest.mark.parametrize("scenario", "ABC")
def test_relative_margin_within_bounds(scenario, path):
    cfg = merged_config(path)
    _, bank_history = run_model(scenario, 202611, cfg)
    p = cfg["parameters"]
    assert bank_history.target_margin.between(p["margin_min"], p["margin_max"]).all()


DRIFT_SEEDS = (202611, 202612, 202613, 202614, 202615)


@pytest.mark.parametrize("path", [
    RELATIVE,
    pytest.param(RELATIVE_NONIM, marks=pytest.mark.xfail(
        strict=True,
        reason="Biến thể không điều kiện nim trôi +0.237 điểm % sau 18 quý "
               "(ghi nhận, chờ nhóm quyết định; không chỉnh tham số)",
    )),
])
def test_relative_drift_small_scenario_a(path):
    """Bình quân qua 5 seed của biên TB quý 18 so với biên khởi đầu: |trôi| <= 0.1.

    Lưu ý: kịch bản A không dùng RNG nên 5 seed cho cùng một kết quả; kiểm tra thực chất là
    một lần chạy, nhiều seed chỉ giữ để bắt hồi quy nếu sau này có thành phần ngẫu nhiên.
    """
    cfg = merged_config(path)
    initial = make_model().banks
    start = sum(b.target_margin for b in initial) / len(initial)
    means = []
    for seed in DRIFT_SEEDS:
        _, bank_history = run_model("A", seed, cfg)
        last = bank_history[bank_history.month == cfg["n_months"]]
        assert len(last) == 8
        means.append(last.target_margin.mean())
    assert abs(sum(means) / len(means) - start) <= 0.1


@pytest.mark.parametrize("path", [RELATIVE, RELATIVE_NONIM])
def test_relative_same_before_policy(path):
    cfg = merged_config(path)
    pm = cfg["parameters"]["policy_month"]
    frames = {s: run_model(s, 202611, cfg)[0] for s in "ABC"}
    pre = lambda f: f[f.month <= pm][["loan_rate", "deposit_rate", "total_loans"]]
    pd.testing.assert_frame_equal(pre(frames["A"]), pre(frames["B"]))
    pd.testing.assert_frame_equal(pre(frames["A"]), pre(frames["C"]))


def test_relative_sensitivity_script_smoke():
    from src.analysis.relative_sensitivity import evaluate, DATASETS
    cfg = merged_config(RELATIVE)
    rows = pd.read_csv(DATASETS["2023Q1"]).to_dict("records")
    out = evaluate(("2023Q1", "rel"), cfg, dict(cfg["parameters"]), rows, [202611])
    assert out["B-A_tb"] < 0 and out["C-A_tb"] < 0
    assert abs(out["troi_bien_q18"]) <= 0.1
    assert out["cham_san_q18"] == 0 and out["cham_tran_q18"] == 0
