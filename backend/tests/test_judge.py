from decimal import Decimal

from conftest import FakeJudgeBackend, FakeTrustLedger

from enclave.models import JudgeVerdict
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank
from enclave.services.judge import JudgeAgent


def _make_disputed_contract(contracts: ContractRegistry, party_a: str, party_b: str) -> str:
    contract = contracts.create_contract(
        party_a, party_b, "deliver 10 vector packs", Decimal("20.0"), tick=1
    )
    contracts.mark_disputed(contract.contract_id)
    return contract.contract_id


async def test_review_fines_the_agent_named_at_fault_by_the_verdict() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(
        at_fault_agent="bob", verdict="bob never delivered", penalty=Decimal("20.0")
    )
    trust = FakeTrustLedger()
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, trust)

    rulings = await judge.review_disputed_contracts(tick=5)

    assert len(rulings) == 1
    assert rulings[0].at_fault_agent == "bob"
    assert bank.get_balance("bob") == Decimal("80.0")


async def test_review_penalizes_trust_from_the_injured_party_towards_the_offender() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(
        at_fault_agent="bob", verdict="bob never delivered", penalty=Decimal("20.0")
    )
    trust = FakeTrustLedger()
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, trust)

    await judge.review_disputed_contracts(tick=5)

    assert trust.adjustments == [("alice", "bob", -0.3)]


async def test_review_marks_the_contract_as_breached() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    contract_id = _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(at_fault_agent="alice", verdict="alice lied", penalty=Decimal("10.0"))
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, FakeTrustLedger())

    await judge.review_disputed_contracts(tick=5)

    assert contracts.get(contract_id).status.value == "breached"


async def test_review_includes_real_transaction_history_as_evidence() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    bank.transfer("alice", "bob", Decimal("20.0"), "advance_payment", tick=1)
    _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(
        at_fault_agent="bob", verdict="bob took the money and ran", penalty=Decimal("20.0")
    )
    backend = FakeJudgeBackend(verdict)
    judge = JudgeAgent(backend, contracts, bank, FakeTrustLedger())

    await judge.review_disputed_contracts(tick=5)

    assert backend.received_dispute_context is not None
    assert "advance_payment" in backend.received_dispute_context


async def test_review_skips_a_verdict_naming_a_non_party_at_fault() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    contract_id = _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(
        at_fault_agent="mallory", verdict="a ghost did it", penalty=Decimal("20.0")
    )
    trust = FakeTrustLedger()
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, trust)

    rulings = await judge.review_disputed_contracts(tick=5)

    assert rulings == []
    assert trust.adjustments == []
    assert bank.get_balance("alice") == Decimal("100.0")
    assert bank.get_balance("bob") == Decimal("100.0")
    assert contracts.get(contract_id).status.value == "disputed"  # sigue pendiente de resolver
