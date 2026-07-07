import type { ReactNode } from "react";

import type { AgentState, AgentStatus } from "../../types/api";

interface ConsciousnessInspectorProps {
  agent: AgentState | null;
  reasoningLog: string[];
  /** Cámara de mapa siguiendo a este agente (Cambio 4b): modo activable/desactivable. */
  isFollowing: boolean;
  onToggleFollow: () => void;
}

const STATUS_META: Record<AgentStatus, { label: string; dot: string; chip: string }> = {
  alive: {
    label: "vivo",
    dot: "bg-enclave-accent shadow-glow",
    chip: "border-enclave-accent/30 text-enclave-accent",
  },
  sleeping: {
    label: "dormido",
    dot: "bg-sky-400",
    chip: "border-sky-400/30 text-sky-400",
  },
  bankrupt: {
    label: "en bancarrota",
    dot: "bg-enclave-danger shadow-glow-danger",
    chip: "border-enclave-danger/30 text-enclave-danger",
  },
  terminated: {
    label: "terminado",
    dot: "bg-enclave-ink-dim",
    chip: "border-enclave-edge text-enclave-ink-dim",
  },
};

function SectionLabel({ children }: { children: ReactNode }) {
  return <h3 className="micro-label mb-1.5">{children}</h3>;
}

function KeyValueRow({ name, value }: { name: string; value: string }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-1 text-xs">
      <span className="truncate text-enclave-ink-mid">{name}</span>
      <span className="shrink-0 tabular-nums text-enclave-ink">{value}</span>
    </li>
  );
}

export function ConsciousnessInspector({
  agent,
  reasoningLog,
  isFollowing,
  onToggleFollow,
}: ConsciousnessInspectorProps) {
  if (!agent) {
    return (
      <section className="panel flex min-h-[180px] shrink-0 flex-col items-center justify-center gap-2 p-6 text-center">
        <span aria-hidden="true" className="text-xl text-enclave-ink-dim">
          ◎
        </span>
        <p className="max-w-[28ch] text-xs leading-relaxed text-enclave-ink-dim">
          Selecciona un ciudadano en el mapa para inspeccionar su conciencia.
        </p>
      </section>
    );
  }

  const statusMeta = STATUS_META[agent.status];

  return (
    <section className="panel shrink-0 overflow-hidden">
      <header className="border-b border-enclave-edge px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="truncate text-sm font-bold tracking-wide text-enclave-ink">
            {agent.display_name}
          </h2>
          <span
            className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${statusMeta.chip}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${statusMeta.dot}`} />
            {statusMeta.label}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <code className="rounded-sm border border-enclave-edge bg-enclave-inset px-1.5 py-0.5 text-[10px] text-enclave-ink-dim">
              {agent.agent_id}
            </code>
            {agent.personality.map((trait) => (
              <span
                key={trait}
                className="rounded-sm border border-enclave-edge bg-enclave-inset px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-enclave-ink-mid"
              >
                {trait}
              </span>
            ))}
          </div>
          <button
            type="button"
            onClick={onToggleFollow}
            aria-pressed={isFollowing}
            className={`shrink-0 rounded-sm border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] transition-colors ${
              isFollowing
                ? "border-enclave-accent/50 bg-enclave-accent/15 text-enclave-accent"
                : "border-enclave-edge text-enclave-ink-dim hover:border-enclave-edge-bright hover:text-enclave-ink"
            }`}
          >
            {isFollowing ? "◉ siguiendo" : "◎ seguir"}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-2 divide-x divide-enclave-edge border-b border-enclave-edge">
        <div className="px-4 py-3">
          <p className="micro-label">Balance</p>
          <p className="mt-1.5 text-lg font-semibold leading-none text-enclave-ink">
            {agent.balance}
            <span className="ml-1 text-[11px] font-medium text-enclave-ink-dim">SC</span>
          </p>
        </div>
        <div className="px-4 py-3">
          <p className="micro-label">Cuota de inferencia</p>
          <p className="mt-1.5 text-lg font-semibold leading-none text-enclave-ink">
            {agent.inference_quota}
          </p>
        </div>
      </div>

      <div className="space-y-4 px-4 py-3">
        <div>
          <SectionLabel>Inventario</SectionLabel>
          {Object.keys(agent.inventory).length === 0 ? (
            <p className="text-xs text-enclave-ink-dim">Sin activos.</p>
          ) : (
            <ul className="divide-y divide-enclave-edge/60">
              {Object.entries(agent.inventory).map(([assetType, quantity]) => (
                <KeyValueRow key={assetType} name={assetType} value={String(quantity)} />
              ))}
            </ul>
          )}
        </div>

        <div>
          <SectionLabel>Confianza</SectionLabel>
          {Object.keys(agent.trust_links).length === 0 ? (
            <p className="text-xs text-enclave-ink-dim">Sin conexiones registradas.</p>
          ) : (
            <ul className="divide-y divide-enclave-edge/60">
              {Object.entries(agent.trust_links).map(([peerId, score]) => (
                <KeyValueRow key={peerId} name={peerId} value={score.toFixed(2)} />
              ))}
            </ul>
          )}
        </div>

        <div>
          <SectionLabel>Flujo de pensamiento</SectionLabel>
          <div className="max-h-48 space-y-1.5 overflow-y-auto rounded border border-enclave-edge bg-black/40 p-2.5 text-[11px] leading-relaxed">
            {reasoningLog.length === 0 ? (
              <p className="text-enclave-ink-dim">Aún no hay razonamiento registrado.</p>
            ) : (
              reasoningLog.map((entry, index) => (
                <p key={index} className="text-enclave-ink-mid">
                  <span aria-hidden="true" className="mr-1.5 select-none text-enclave-accent">
                    ▸
                  </span>
                  {entry}
                </p>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
