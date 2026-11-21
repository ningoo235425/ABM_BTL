
"""Kiểm thử mô hình ABM dùng Mesa 3.3.1."""

import pandas as pd
import pytest

from mesa import Agent, Model

from src.core.model import ABMModel
from src.agents.bank import Bank
from src.agents.depositors import DepositorBlock
from src.agents.borrowers import BorrowerBlock
from src.agents.regulator import Regulator


def test_mesa_architecture():
    """Các thành phần phải kế thừa Mesa.Agent."""
    model = ABMModel(seed=123)

    assert isinstance(model, Model)

    for bank in model.banks:
        assert isinstance(bank, Agent)
        assert bank.model is model

    assert isinstance(model.regulator, Agent)
    assert isinstance(model.depositor, Agent)
    assert isinstance(model.borrower, Agent)

    assert len(model.banks) == 9
    assert len(model.agents) == 12


def test_depositors_react_to_rate():
    model = ABMModel()
    depositor = model.depositor

    assert depositor.growth(6, 5) > depositor.growth(4, 5)


def test_borrowers_react_to_rate():
    model = ABMModel()
    borrower = model.borrower

    assert (
        borrower.desired_growth(8)
        > borrower.desired_growth(11)
    )


def test_compliance_soft():
    model = ABMModel()
    regulator = model.regulator

    p = regulator.compliance_probability(2.5)

    assert 0 < p < 1


def test_policy_activation():
    model = ABMModel(scenario="B")

    model.regulator.step()
    assert not model.regulator.policy_active

    model.month = 14
    model.regulator.step()

    assert model.regulator.policy_active


def test_reproducible():
    """Cùng seed phải cho cùng kết quả."""
    a = ABMModel("B", seed=123).run()
    b = ABMModel("B", seed=123).run()

    pd.testing.assert_frame_equal(a, b)


def test_invariants():
    for scenario in "ABC":
        model = ABMModel(scenario, seed=10)
        frame = model.run()

        assert len(frame) == 24

        cols = [
            "deposit_rate",
            "loan_rate",
            "total_loans",
            "total_deposits",
        ]

        assert (frame[cols] >= 0).all().all()

        assert (
            frame.loan_deposit_ratio <= 1.60 + 1e-9
        ).all()


def test_policies_vs_baseline():
    """Kiểm tra hành vi trong cấu hình minh họa."""
    a = ABMModel("A", seed=5).run()
    b = ABMModel("B", seed=5).run()

    assert (
        b.loan_rate.iloc[-1]
        < a.loan_rate.iloc[-1]
    )


def test_csv_missing_required_columns(tmp_path):
    path = tmp_path / "banks.csv"

    path.write_text(
        "bank_id,deposits\nA,100\n"
    )

    with pytest.raises(ValueError):
        ABMModel.from_clean_csv(path)


def test_validation_checks():
    from src.analysis.validation import run_validation

    checks = run_validation()

    assert all(checks.values())
