import { useMemo } from "react";

import type {
  AgentState,
  AssetType,
  Contract,
  ContractStatus,
  JudgeRuling,
  MarketOffer,
} from "../../types/api";

interface ActivityFeedProps {
  offers: MarketOffer[];
  contracts: Contract[];
  rulings: JudgeRuling[];
  agents: AgentState[];
}

const ASSET_LABELS: Record<AssetType, string> = {
  inference_quota: "cuota de inferencia",
  vector_pack: "vector pack",
  alpha_signal: "señal alfa",
  code_script: "script",
  financial_derivative: "derivado",
};

const CONTRACT_STATUS_META: Record<ContractStatus, { label: string; chip: string }> = {
  pending: { label: "pendiente", chip: "border-enclave-warn/40 text-enclave-warn" },
  disputed: { label: "en disputa", chip: "border-enclave-danger/40 text-enclave-danger" },
  fulfilled: { label: "cumplido", chip: "border-enclave-accent/40 text-enclave-accent" },
  breached: { label: "incumplido", chip: "border-enclave-danger/40 text-enclave-danger" },
};

/** Ítems mostrados por sección: es un feed de un vistazo, no un histórico completo. */
const MAX_ITEMS_PER_SECTION = 6;

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="flex items-baseline justify-between">
      <h3 className="micro-label text-enclave-accent">{title}</h3>
      <span className="text-[10px] tabular-nums text-enclave-ink-dim">{count}</span>
    </div>
  );
}

function EmptyRow({ children }: { children: string }) {
  return <p className="text-[11px] leading-relaxed text-enclave-ink-dim">{children}</p>;
}

/**
 * Feed de actividad económica en vivo: ofertas abiertas del mercado, contratos
 * sin resolver y últimos veredictos del Agente Juez — la parte de la economía
 * que el backend ya calculaba pero era invisible para el observador.
 */
export function ActivityFeed({ offers, contracts, rulings, agents }: ActivityFeedProps) {
  const nameById = useMemo(
    () => new Map(agents.map((agent) => [agent.agent_id, agent.display_name])),
    [agents],
  );
  const displayName = (agentId: string): string => nameById.get(agentId) ?? agentId;

  return (
    <section className="panel shrink-0">
      <header className="flex items-center justify-between border-b border-enclave-edge px-4 py-2">
        <h2 className="micro-label text-enclave-ink-mid">Actividad económica</h2>
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            offers.length + contracts.length + rulings.length > 0
              ? "bg-enclave-accent shadow-glow"
              : "bg-enclave-edge-bright"
          }`}
          title="actividad del mercado, contratos y juez"
        />
      </header>

      <div className="space-y-4 p-3">
        <div className="space-y-1.5">
          <SectionHeader title="Ofertas en el mercado" count={offers.length} />
          {offers.length === 0 ? (
            <EmptyRow>No hay ofertas abiertas en el tablón.</EmptyRow>
          ) : (
            <ul className="divide-y divide-enclave-edge/60">
              {offers.slice(0, MAX_ITEMS_PER_SECTION).map((offer) => (
                <li
                  key={offer.offer_id}
                  className="flex items-baseline justify-between gap-2 py-1 text-[11px]"
                >
                  <span className="truncate text-enclave-ink-mid">
                    <span className="text-enclave-ink">{displayName(offer.seller_id)}</span>
                    {" vende "}
                    {offer.quantity}× {ASSET_LABELS[offer.asset_type]}
                  </span>
                  <span className="shrink-0 tabular-nums text-enclave-ink">
                    {offer.unit_price}
                    <span className="ml-0.5 text-enclave-ink-dim">SC/u</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-1.5">
          <SectionHeader title="Contratos sin resolver" count={contracts.length} />
          {contracts.length === 0 ? (
            <EmptyRow>No hay contratos pendientes ni en disputa.</EmptyRow>
          ) : (
            <ul className="divide-y divide-enclave-edge/60">
              {contracts.slice(0, MAX_ITEMS_PER_SECTION).map((contract) => {
                const statusMeta = CONTRACT_STATUS_META[contract.status];
                return (
                  <li key={contract.contract_id} className="space-y-0.5 py-1.5 text-[11px]">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-enclave-ink">
                        {displayName(contract.party_a)} ⇄ {displayName(contract.party_b)}
                      </span>
                      <span
                        className={`shrink-0 rounded-full border px-1.5 py-px text-[9px] font-semibold uppercase tracking-[0.1em] ${statusMeta.chip}`}
                      >
                        {statusMeta.label}
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between gap-2 text-enclave-ink-dim">
                      <span className="truncate">{contract.terms}</span>
                      <span className="shrink-0 tabular-nums">
                        {contract.amount}
                        <span className="ml-0.5">SC</span>
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="space-y-1.5">
          <SectionHeader title="Veredictos del Juez" count={rulings.length} />
          {rulings.length === 0 ? (
            <EmptyRow>El Agente Juez aún no ha dictado ningún veredicto.</EmptyRow>
          ) : (
            <ul className="divide-y divide-enclave-edge/60">
              {rulings.slice(0, MAX_ITEMS_PER_SECTION).map((ruling) => (
                <li key={ruling.ruling_id} className="space-y-0.5 py-1.5 text-[11px]">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-enclave-ink">
                      <span aria-hidden="true" className="mr-1 select-none text-enclave-danger">
                        ⚖
                      </span>
                      {displayName(ruling.at_fault_agent)} culpable
                    </span>
                    <span className="shrink-0 tabular-nums text-enclave-danger">
                      −{ruling.penalty}
                      <span className="ml-0.5">SC</span>
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between gap-2 text-enclave-ink-dim">
                    <span className="truncate">{ruling.verdict}</span>
                    <span className="shrink-0 tabular-nums">t{ruling.ruled_at_tick}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
