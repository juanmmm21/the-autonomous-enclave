from decimal import Decimal

import pytest

from enclave.exceptions import InsufficientFundsError
from enclave.services.economy import CENTRAL_BANK_TREASURY_ID, CentralBank, compute_gini_index


@pytest.fixture
def bank() -> CentralBank:
    bank = CentralBank(passive_tick_cost=Decimal("2.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("10.0"))
    return bank


def test_transfer_moves_balance_between_agents(bank: CentralBank) -> None:
    bank.transfer("alice", "bob", Decimal("30.0"), "test_transfer", tick=1)

    assert bank.get_balance("alice") == Decimal("70.0")
    assert bank.get_balance("bob") == Decimal("40.0")


def test_transfer_rejects_non_positive_amount(bank: CentralBank) -> None:
    with pytest.raises(ValueError, match="positive"):
        bank.transfer("alice", "bob", Decimal("0"), "invalid", tick=1)


def test_transfer_raises_when_funds_are_insufficient(bank: CentralBank) -> None:
    with pytest.raises(InsufficientFundsError) as exc_info:
        bank.transfer("bob", "alice", Decimal("999.0"), "overdraft", tick=1)

    assert exc_info.value.agent_id == "bob"


def test_apply_passive_tick_cost_charges_and_stays_alive(bank: CentralBank) -> None:
    transaction, is_bankrupt = bank.apply_passive_tick_cost("alice", tick=1)

    assert bank.get_balance("alice") == Decimal("98.0")
    assert transaction.amount == Decimal("2.0")
    assert transaction.to_agent == CENTRAL_BANK_TREASURY_ID
    assert is_bankrupt is False


def test_apply_passive_tick_cost_clamps_balance_at_zero(bank: CentralBank) -> None:
    bank.open_account("carol", Decimal("1.0"))

    _, is_bankrupt = bank.apply_passive_tick_cost("carol", tick=1)

    assert bank.get_balance("carol") == Decimal("0")
    assert is_bankrupt is True


def test_apply_passive_tick_cost_on_already_bankrupt_agent_stays_at_zero(
    bank: CentralBank,
) -> None:
    bank.open_account("dave", Decimal("0"))

    _, is_bankrupt = bank.apply_passive_tick_cost("dave", tick=1)

    assert bank.get_balance("dave") == Decimal("0")
    assert is_bankrupt is True


def test_apply_penalty_moves_funds_to_treasury(bank: CentralBank) -> None:
    bank.apply_penalty("alice", Decimal("15.0"), tick=1)

    assert bank.get_balance("alice") == Decimal("85.0")
    assert bank.get_balance(CENTRAL_BANK_TREASURY_ID) == Decimal("15.0")


def test_all_balances_excludes_treasury(bank: CentralBank) -> None:
    balances = bank.all_balances()

    assert CENTRAL_BANK_TREASURY_ID not in balances
    assert balances == {"alice": Decimal("100.0"), "bob": Decimal("10.0")}


def test_gini_index_is_zero_for_perfect_equality() -> None:
    assert compute_gini_index([Decimal("50"), Decimal("50"), Decimal("50")]) == 0.0


def test_gini_index_is_zero_with_fewer_than_two_positive_balances() -> None:
    assert compute_gini_index([Decimal("50")]) == 0.0
    assert compute_gini_index([]) == 0.0


def test_gini_index_reflects_concentration() -> None:
    equal = compute_gini_index([Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10")])
    concentrated = compute_gini_index([Decimal("1"), Decimal("1"), Decimal("1"), Decimal("97")])

    assert equal < concentrated
    assert 0.0 <= concentrated <= 1.0
