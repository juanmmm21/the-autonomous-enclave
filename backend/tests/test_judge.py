from decimal import Decimal

from conftest import FakeJudgeBackend, FakeTrustLedger

from enclave.exceptions import LLMGenerationError
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


class _FailingThenFakeJudgeBackend(FakeJudgeBackend):
    """Falla en la primera adjudicación (veredicto ilegible) y responde bien después."""

    def __init__(self, verdict: JudgeVerdict) -> None:
        super().__init__(verdict)
        self.calls = 0

    async def adjudicate(
        self, system_prompt: str, contract: object, dispute_context: str
    ) -> object:
        self.calls += 1
        if self.calls == 1:
            raise LLMGenerationError("judge produced a malformed verdict")
        return await super().adjudicate(system_prompt, contract, dispute_context)


async def test_review_skips_a_malformed_verdict_and_still_resolves_other_contracts() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    first_id = _make_disputed_contract(contracts, "alice", "bob")
    second_id = _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(at_fault_agent="bob", verdict="bob defaulted", penalty=Decimal("10.0"))
    backend = _FailingThenFakeJudgeBackend(verdict)
    judge = JudgeAgent(backend, contracts, bank, FakeTrustLedger())

    rulings = await judge.review_disputed_contracts(tick=5)

    # El primer contrato queda en disputa para reintentarlo; el segundo se resuelve.
    assert backend.calls == 2
    assert len(rulings) == 1
    resolved = {contracts.get(first_id).status.value, contracts.get(second_id).status.value}
    assert resolved == {"disputed", "breached"}


async def test_review_caps_the_penalty_at_the_offenders_available_balance() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("15.0"))
    contract_id = _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(
        at_fault_agent="bob", verdict="bob never delivered", penalty=Decimal("50.0")
    )
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, FakeTrustLedger())

    rulings = await judge.review_disputed_contracts(tick=5)

    # Mismo criterio que el coste pasivo: un culpable insolvente paga lo que tiene.
    assert bank.get_balance("bob") == Decimal("0")
    assert rulings[0].penalty == Decimal("15.0")
    assert contracts.get(contract_id).status.value == "breached"


async def test_review_with_zero_penalty_still_marks_breach_and_docks_trust() -> None:
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("100.0"))
    contract_id = _make_disputed_contract(contracts, "alice", "bob")
    verdict = JudgeVerdict(at_fault_agent="bob", verdict="symbolic ruling", penalty=Decimal("0"))
    trust = FakeTrustLedger()
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, trust)

    rulings = await judge.review_disputed_contracts(tick=5)

    assert bank.get_balance("bob") == Decimal("100.0")  # sin multa que cobrar
    assert trust.adjustments == [("alice", "bob", -0.3)]
    assert contracts.get(contract_id).status.value == "breached"
    assert rulings[0].penalty == Decimal("0")


async def test_review_handles_an_at_fault_party_without_a_bank_account() -> None:
    # Un agente puede firmar un contrato con una contraparte inventada por el LLM;
    # si el Juez la declara culpable, no hay cuenta que multar pero el contrato
    # debe cerrarse igualmente.
    contracts = ContractRegistry()
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    contract_id = _make_disputed_contract(contracts, "alice", "ghost")
    verdict = JudgeVerdict(
        at_fault_agent="ghost", verdict="ghost never existed, let alone paid", penalty=Decimal("20")
    )
    judge = JudgeAgent(FakeJudgeBackend(verdict), contracts, bank, FakeTrustLedger())

    rulings = await judge.review_disputed_contracts(tick=5)

    assert rulings[0].penalty == Decimal("0")
    assert contracts.get(contract_id).status.value == "breached"
