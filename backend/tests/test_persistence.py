from decimal import Decimal

from enclave.services.economy import CENTRAL_BANK_TREASURY_ID, CentralBank
from enclave.services.inference_market import InferenceQuotaLedger
from enclave.services.persistence import _apply_restored_state, _snapshot_rows


def test_snapshot_rows_includes_treasury_and_every_citizen_balance() -> None:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("100.0"))
    bank.open_account("bob", Decimal("10.0"))
    bank.apply_penalty("alice", Decimal("5.0"), tick=1)  # mueve algo al tesoro
    quotas = InferenceQuotaLedger()
    quotas.open_account("alice", 3)
    quotas.open_account("bob", 5)

    balance_rows, quota_rows = _snapshot_rows(bank, quotas)

    assert dict(balance_rows) == {
        CENTRAL_BANK_TREASURY_ID: Decimal("5.0"),
        "alice": Decimal("95.0"),
        "bob": Decimal("10.0"),
    }
    assert dict(quota_rows) == {"alice": 3, "bob": 5}


def test_apply_restored_state_overwrites_freshly_seeded_accounts() -> None:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("150.0"))  # balance de partida "fresco"
    quotas = InferenceQuotaLedger()
    quotas.open_account("alice", 3)

    _apply_restored_state(
        bank,
        quotas,
        balance_rows=[("alice", Decimal("42.0")), (CENTRAL_BANK_TREASURY_ID, Decimal("8.0"))],
        quota_rows=[("alice", 1)],
    )

    assert bank.get_balance("alice") == Decimal("42.0")
    assert bank.get_balance(CENTRAL_BANK_TREASURY_ID) == Decimal("8.0")
    assert quotas.get_quota("alice") == 1


def test_snapshot_then_restore_round_trips_the_full_economic_state() -> None:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("alice", Decimal("77.0"))
    bank.open_account("bob", Decimal("33.0"))
    quotas = InferenceQuotaLedger()
    quotas.open_account("alice", 4)
    quotas.open_account("bob", 2)

    balance_rows, quota_rows = _snapshot_rows(bank, quotas)

    fresh_bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    fresh_bank.open_account("alice", Decimal("150.0"))
    fresh_bank.open_account("bob", Decimal("150.0"))
    fresh_quotas = InferenceQuotaLedger()
    fresh_quotas.open_account("alice", 3)
    fresh_quotas.open_account("bob", 3)

    _apply_restored_state(fresh_bank, fresh_quotas, balance_rows, quota_rows)

    assert fresh_bank.all_balances() == bank.all_balances()
    assert fresh_quotas.all_quotas() == quotas.all_quotas()
