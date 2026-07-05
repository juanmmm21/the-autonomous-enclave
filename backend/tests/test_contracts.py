from decimal import Decimal

import pytest

from enclave.services.contracts import ContractNotFoundError, ContractRegistry


@pytest.fixture
def contracts() -> ContractRegistry:
    return ContractRegistry()


def test_create_contract_starts_as_pending(contracts: ContractRegistry) -> None:
    contract = contracts.create_contract("alice", "bob", "deliver goods", Decimal("10.0"), tick=1)

    assert contract.status.value == "pending"
    assert contracts.get(contract.contract_id) == contract


def test_get_unknown_contract_raises_contract_not_found_error(contracts: ContractRegistry) -> None:
    with pytest.raises(ContractNotFoundError):
        contracts.get("unknown-id")


def test_mark_fulfilled_disputed_and_breached_transition_status(
    contracts: ContractRegistry,
) -> None:
    fulfilled = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=1)
    disputed = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=1)
    breached = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=1)

    contracts.mark_fulfilled(fulfilled.contract_id)
    contracts.mark_disputed(disputed.contract_id)
    contracts.mark_breached(breached.contract_id)

    assert contracts.get(fulfilled.contract_id).status.value == "fulfilled"
    assert contracts.get(disputed.contract_id).status.value == "disputed"
    assert contracts.get(breached.contract_id).status.value == "breached"


def test_disputed_contracts_returns_only_disputed_ones(contracts: ContractRegistry) -> None:
    pending = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=1)
    disputed = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=1)
    contracts.mark_disputed(disputed.contract_id)

    result_ids = {c.contract_id for c in contracts.disputed_contracts()}

    assert result_ids == {disputed.contract_id}
    assert pending.contract_id not in result_ids


def test_expire_overdue_contracts_escalates_only_pending_ones_past_the_grace_period(
    contracts: ContractRegistry,
) -> None:
    overdue = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=0)
    within_grace = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=8)
    already_fulfilled = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=0)
    contracts.mark_fulfilled(already_fulfilled.contract_id)

    expired = contracts.expire_overdue_contracts(current_tick=10, grace_period_ticks=10)

    assert [c.contract_id for c in expired] == [overdue.contract_id]
    assert contracts.get(overdue.contract_id).status.value == "disputed"
    assert contracts.get(within_grace.contract_id).status.value == "pending"
    assert contracts.get(already_fulfilled.contract_id).status.value == "fulfilled"


def test_expire_overdue_contracts_is_idempotent(contracts: ContractRegistry) -> None:
    contract = contracts.create_contract("alice", "bob", "terms", Decimal("1.0"), tick=0)

    first_pass = contracts.expire_overdue_contracts(current_tick=10, grace_period_ticks=10)
    second_pass = contracts.expire_overdue_contracts(current_tick=20, grace_period_ticks=10)

    assert len(first_pass) == 1
    assert second_pass == []  # ya estaba DISPUTED, no se vuelve a escalar
    assert contracts.get(contract.contract_id).status.value == "disputed"
