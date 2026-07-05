import { useEffect, useMemo, useState } from "react";

import { ConsciousnessInspector } from "./components/dashboard/ConsciousnessInspector";
import { DivineConsole } from "./components/dashboard/DivineConsole";
import { EconomyPanel } from "./components/dashboard/EconomyPanel";
import { GameCanvas } from "./components/phaser/GameCanvas";
import { useTelemetrySocket } from "./hooks/useTelemetrySocket";
import type { ConnectionStatus } from "./hooks/useTelemetrySocket";

const TELEMETRY_WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/api/v1/ws/telemetry`;
const MAX_REASONING_LOG_ENTRIES = 30;

const CONNECTION_META: Record<
  ConnectionStatus,
  { label: string; dot: string; pill: string }
> = {
  open: {
    label: "en línea",
    dot: "bg-enclave-accent shadow-glow",
    pill: "border-enclave-accent/30 text-enclave-accent",
  },
  connecting: {
    label: "conectando…",
    dot: "animate-pulse bg-enclave-warn shadow-glow-warn",
    pill: "border-enclave-warn/30 text-enclave-warn",
  },
  closed: {
    label: "sin conexión",
    dot: "animate-pulse bg-enclave-danger shadow-glow-danger",
    pill: "border-enclave-danger/30 text-enclave-danger",
  },
};

export function App() {
  const { latestEvent, status } = useTelemetrySocket(TELEMETRY_WS_URL);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [reasoningLog, setReasoningLog] = useState<string[]>([]);

  const agents = useMemo(() => latestEvent?.agents ?? [], [latestEvent]);
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.agent_id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );

  // El vaciado se declara ANTES que el append: al cambiar de agente ambos efectos
  // se disparan en el mismo commit y, en orden de declaración, primero se limpia
  // el log del agente anterior y después se añade el razonamiento del nuevo.
  useEffect(() => {
    setReasoningLog([]);
  }, [selectedAgentId]);

  useEffect(() => {
    if (selectedAgent?.last_reasoning) {
      setReasoningLog((previous) =>
        [...previous, `[tick ${latestEvent?.tick}] ${selectedAgent.last_reasoning}`].slice(
          -MAX_REASONING_LOG_ENTRIES,
        ),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo reacciona a nuevo razonamiento del agente seleccionado
  }, [selectedAgent?.last_reasoning]);

  const connection = CONNECTION_META[status];
  const tickReadout = String(latestEvent?.tick ?? 0).padStart(4, "0");

  return (
    <div className="flex min-h-screen flex-col bg-enclave-bg">
      <header className="sticky top-0 z-10 border-b border-enclave-edge bg-enclave-bg/90 backdrop-blur">
        <div className="flex h-12 items-center justify-between gap-4 px-5">
          <div className="flex min-w-0 items-center gap-3">
            <span
              aria-hidden="true"
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-sm border border-enclave-accent/40 bg-enclave-accent/10 text-xs font-bold text-enclave-accent"
            >
              ◈
            </span>
            <div className="flex min-w-0 items-baseline gap-3">
              <h1 className="truncate text-sm font-bold uppercase tracking-[0.18em] text-enclave-ink">
                The Autonomous Enclave
              </h1>
              <span className="hidden whitespace-nowrap text-[11px] uppercase tracking-[0.14em] text-enclave-ink-dim md:inline">
                Silicon Polis · Modo Dios
              </span>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-4">
            <div className="hidden items-baseline gap-1.5 sm:flex">
              <span className="micro-label">tick</span>
              <span className="text-sm font-semibold text-enclave-ink">{tickReadout}</span>
            </div>
            <div className="hidden items-baseline gap-1.5 sm:flex">
              <span className="micro-label">ciudadanos</span>
              <span className="text-sm font-semibold text-enclave-ink">{agents.length}</span>
            </div>
            <span
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${connection.pill}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${connection.dot}`} />
              {connection.label}
            </span>
          </div>
        </div>
      </header>

      <main className="grid flex-1 grid-cols-1 items-start gap-4 p-4 lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:p-5">
        <div className="flex flex-col gap-4">
          <section className="panel overflow-hidden">
            <div className="flex items-center justify-between border-b border-enclave-edge px-4 py-2">
              <h2 className="micro-label text-enclave-ink-mid">Mapa de la colonia</h2>
              <span className="micro-label">vista de rejilla</span>
            </div>
            <div className="bg-enclave-inset p-3">
              <GameCanvas agents={agents} onSelectAgent={setSelectedAgentId} />
            </div>
          </section>
          <EconomyPanel indicators={latestEvent?.indicators ?? null} />
        </div>
        <aside className="flex flex-col gap-4">
          <ConsciousnessInspector agent={selectedAgent} reasoningLog={reasoningLog} />
          <DivineConsole selectedAgentId={selectedAgentId} />
        </aside>
      </main>
    </div>
  );
}
