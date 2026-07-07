import { useMemo } from "react";

import type { AgentState, AgentStatus } from "../../types/api";
import { citizenAccentCssFor } from "../phaser/tileset";

interface CitizenCensusProps {
  agents: AgentState[];
  selectedAgentId: string | null;
  onSelectAgent: (agentId: string) => void;
}

const STATUS_DOT: Record<AgentStatus, string> = {
  alive: "bg-enclave-accent shadow-glow",
  sleeping: "bg-sky-400",
  bankrupt: "bg-enclave-danger shadow-glow-danger",
  terminated: "bg-enclave-ink-dim",
};

/**
 * Censo de la colonia: lista completa de ciudadanos ordenada por riqueza, con
 * su punto de acento (el mismo que llevan junto al nombre en el mapa), estado
 * y balance. Con muchos más ciudadanos que sprites diminutos, es la forma
 * rápida de localizar y seleccionar a cualquiera sin buscarlo por el mapa.
 */
export function CitizenCensus({ agents, selectedAgentId, onSelectAgent }: CitizenCensusProps) {
  // Orden por balance descendente: el censo dobla como ranking de riqueza.
  // `Number` solo para ordenar; el balance mostrado conserva el string decimal.
  const sortedAgents = useMemo(
    () => [...agents].sort((a, b) => Number(b.balance) - Number(a.balance)),
    [agents],
  );

  return (
    <section className="panel">
      <header className="flex items-center justify-between border-b border-enclave-edge px-4 py-2">
        <h2 className="micro-label text-enclave-ink-mid">Censo de ciudadanos</h2>
        <span className="text-[10px] tabular-nums text-enclave-ink-dim">{agents.length}</span>
      </header>

      {sortedAgents.length === 0 ? (
        <p className="p-3 text-[11px] leading-relaxed text-enclave-ink-dim">
          Aún no hay ciudadanos registrados.
        </p>
      ) : (
        <ul className="max-h-56 overflow-y-auto p-1.5">
          {sortedAgents.map((agent) => {
            const isSelected = agent.agent_id === selectedAgentId;
            return (
              <li key={agent.agent_id}>
                <button
                  type="button"
                  onClick={() => onSelectAgent(agent.agent_id)}
                  aria-pressed={isSelected}
                  className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-[11px] transition-colors ${
                    isSelected
                      ? "bg-enclave-accent/10 text-enclave-ink"
                      : "text-enclave-ink-mid hover:bg-enclave-inset hover:text-enclave-ink"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: citizenAccentCssFor(agent.agent_id) }}
                  />
                  <span className="min-w-0 flex-1 truncate">{agent.display_name}</span>
                  <span
                    aria-hidden="true"
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${STATUS_DOT[agent.status]}`}
                    title={agent.status}
                  />
                  <span className="shrink-0 tabular-nums text-enclave-ink">
                    {agent.balance}
                    <span className="ml-0.5 text-[9px] text-enclave-ink-dim">SC</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
