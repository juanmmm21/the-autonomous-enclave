import { useCallback, useEffect, useMemo, useState } from "react";

import { ActivityFeed } from "./components/dashboard/ActivityFeed";
import { CitizenCensus } from "./components/dashboard/CitizenCensus";
import { CitizenFoundry } from "./components/dashboard/CitizenFoundry";
import { ConsciousnessInspector } from "./components/dashboard/ConsciousnessInspector";
import { DivineConsole } from "./components/dashboard/DivineConsole";
import { EconomyPanel } from "./components/dashboard/EconomyPanel";
import { HelpOverlay } from "./components/dashboard/HelpOverlay";
import { GameCanvas } from "./components/phaser/GameCanvas";
import { useTelemetrySocket } from "./hooks/useTelemetrySocket";
import type { ConnectionStatus } from "./hooks/useTelemetrySocket";

const TELEMETRY_WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/api/v1/ws/telemetry`;
const MAX_REASONING_LOG_ENTRIES = 30;
const HELP_SEEN_STORAGE_KEY = "enclave:help-seen";

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
  const [followAgentId, setFollowAgentId] = useState<string | null>(null);
  const [reasoningLog, setReasoningLog] = useState<string[]>([]);
  const [isAsideOpen, setIsAsideOpen] = useState(true);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  // Se abre automáticamente en la primera visita (flag en localStorage), y a
  // partir de ahí solo mediante el botón "?" del header.
  useEffect(() => {
    if (!window.localStorage.getItem(HELP_SEEN_STORAGE_KEY)) {
      setIsHelpOpen(true);
      window.localStorage.setItem(HELP_SEEN_STORAGE_KEY, "true");
    }
  }, []);

  const agents = useMemo(() => latestEvent?.agents ?? [], [latestEvent]);
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.agent_id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );
  const simTime = useMemo(
    () =>
      latestEvent ? { tick: latestEvent.tick, ticksPerDay: latestEvent.ticks_per_day } : null,
    [latestEvent],
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

  // Seleccionar otro ciudadano cancela el seguimiento de cámara del anterior;
  // activarlo de nuevo sobre el mismo agente seleccionado es responsabilidad
  // del botón "seguir" del Inspector de Conciencia, no de este efecto.
  useEffect(() => {
    setFollowAgentId(null);
  }, [selectedAgentId]);

  const handleToggleFollow = useCallback(() => {
    setFollowAgentId((current) => (current ? null : selectedAgentId));
  }, [selectedAgentId]);

  // Referencia estable: `MainScene` la asigna una única vez en su evento "ready".
  const handleFollowCancelled = useCallback(() => setFollowAgentId(null), []);

  const connection = CONNECTION_META[status];
  const tickReadout = String(latestEvent?.tick ?? 0).padStart(4, "0");

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-enclave-bg">
      <header className="z-20 border-b border-enclave-edge bg-enclave-bg/90 backdrop-blur">
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
            <button
              type="button"
              onClick={() => setIsAsideOpen((open) => !open)}
              aria-label={isAsideOpen ? "Ocultar panel lateral" : "Mostrar panel lateral"}
              className="flex h-6 w-6 items-center justify-center rounded-sm border border-enclave-edge text-xs text-enclave-ink-dim transition-colors hover:border-enclave-edge-bright hover:text-enclave-ink"
            >
              {isAsideOpen ? "»" : "«"}
            </button>
            <button
              type="button"
              onClick={() => setIsHelpOpen(true)}
              aria-label="Abrir ayuda"
              className="flex h-6 w-6 items-center justify-center rounded-full border border-enclave-accent/40 bg-enclave-accent/10 text-xs font-bold text-enclave-accent transition-colors hover:bg-enclave-accent/20"
            >
              ?
            </button>
          </div>
        </div>
      </header>

      <main className="relative flex flex-1 overflow-hidden">
        <div className="relative min-w-0 flex-1">
          <GameCanvas
            agents={agents}
            onSelectAgent={setSelectedAgentId}
            followAgentId={followAgentId}
            onFollowCancelled={handleFollowCancelled}
            simTime={simTime}
          />
          <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-2 rounded-full border border-enclave-edge bg-enclave-bg/80 px-3 py-1 backdrop-blur">
            <span className="micro-label">Mapa de la colonia</span>
          </div>
        </div>

        <aside
          className={`flex shrink-0 flex-col gap-3 overflow-y-auto border-l border-enclave-edge bg-enclave-panel transition-[width,padding] duration-200 ${
            isAsideOpen ? "w-[22rem] p-3" : "w-0 overflow-hidden p-0"
          }`}
        >
          <EconomyPanel indicators={latestEvent?.indicators ?? null} />
          <ActivityFeed
            offers={latestEvent?.market_offers ?? []}
            contracts={latestEvent?.open_contracts ?? []}
            rulings={latestEvent?.recent_rulings ?? []}
            agents={agents}
          />
          <CitizenCensus
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
          />
          <ConsciousnessInspector
            agent={selectedAgent}
            reasoningLog={reasoningLog}
            isFollowing={followAgentId !== null && followAgentId === selectedAgentId}
            onToggleFollow={handleToggleFollow}
          />
          <DivineConsole selectedAgentId={selectedAgentId} />
          <CitizenFoundry />
        </aside>
      </main>

      <HelpOverlay open={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
    </div>
  );
}
