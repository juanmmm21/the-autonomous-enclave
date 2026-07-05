"""Persistencia periódica del estado económico en Postgres.

`CentralBank` e `InferenceQuotaLedger` siguen viviendo en memoria durante la
ejecución (evita I/O de red en el camino caliente de cada tick); este servicio
solo hace snapshot/restauración del estado agregado (balances y cuotas), no
persiste cada mutación individual. Un checkpoint se toma al final de cada
jornada simulada y al apagar el proceso limpiamente (ver `main.py`), así que
como mucho se pierde un día de estado ante un crash no controlado.
"""

from __future__ import annotations

from decimal import Decimal

import asyncpg

from enclave.services.economy import CENTRAL_BANK_TREASURY_ID, CentralBank
from enclave.services.inference_market import InferenceQuotaLedger

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_balances (
    agent_id TEXT PRIMARY KEY,
    balance NUMERIC NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_quotas (
    agent_id TEXT PRIMARY KEY,
    quota INTEGER NOT NULL
);
"""


def _snapshot_rows(
    bank: CentralBank, quotas: InferenceQuotaLedger
) -> tuple[list[tuple[str, Decimal]], list[tuple[str, int]]]:
    """Construye las filas a persistir a partir del estado en memoria. Función
    pura (sin I/O) para poder testearla sin una base de datos real."""
    balance_rows = [(CENTRAL_BANK_TREASURY_ID, bank.get_balance(CENTRAL_BANK_TREASURY_ID))]
    balance_rows.extend(bank.all_balances().items())
    quota_rows = list(quotas.all_quotas().items())
    return balance_rows, quota_rows


def _apply_restored_state(
    bank: CentralBank,
    quotas: InferenceQuotaLedger,
    balance_rows: list[tuple[str, Decimal]],
    quota_rows: list[tuple[str, int]],
) -> None:
    """Aplica filas restauradas sobre el banco y el ledger de cuotas en memoria.
    Función pura (sin I/O) para poder testearla sin una base de datos real."""
    for agent_id, balance in balance_rows:
        bank.open_account(agent_id, balance)
    for agent_id, quota in quota_rows:
        quotas.open_account(agent_id, quota)


class PostgresLedgerStore:
    """Checkpoint/restauración del estado económico agregado en Postgres."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def has_saved_state(self) -> bool:
        pool = self._require_pool()
        row = await pool.fetchrow("SELECT 1 FROM agent_balances LIMIT 1")
        return row is not None

    async def save_snapshot(self, bank: CentralBank, quotas: InferenceQuotaLedger) -> None:
        pool = self._require_pool()
        balance_rows, quota_rows = _snapshot_rows(bank, quotas)
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute("TRUNCATE agent_balances, agent_quotas")
            if balance_rows:
                await conn.executemany(
                    "INSERT INTO agent_balances (agent_id, balance) VALUES ($1, $2)",
                    balance_rows,
                )
            if quota_rows:
                await conn.executemany(
                    "INSERT INTO agent_quotas (agent_id, quota) VALUES ($1, $2)",
                    quota_rows,
                )

    async def restore(self, bank: CentralBank, quotas: InferenceQuotaLedger) -> bool:
        """Restaura el último snapshot guardado sobre `bank`/`quotas`, que deben
        haberse poblado ya con las cuentas por defecto (`seed_initial_citizens`).
        Devuelve `False` sin tocar nada si no hay ningún snapshot previo."""
        pool = self._require_pool()
        balance_records = await pool.fetch("SELECT agent_id, balance FROM agent_balances")
        if not balance_records:
            return False
        quota_records = await pool.fetch("SELECT agent_id, quota FROM agent_quotas")

        balance_rows = [(r["agent_id"], r["balance"]) for r in balance_records]
        quota_rows = [(r["agent_id"], r["quota"]) for r in quota_records]
        _apply_restored_state(bank, quotas, balance_rows, quota_rows)
        return True

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgresLedgerStore.connect() must be awaited before use")
        return self._pool
