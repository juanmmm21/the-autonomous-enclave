import { useEffect, useMemo, useState } from "react";

import { ConsciousnessInspector } from "./components/dashboard/ConsciousnessInspector";
import { DivineConsole } from "./components/dashboard/DivineConsole";
import { EconomyPanel } from "./components/dashboard/EconomyPanel";
import { GameCanvas } from "./components/phaser/GameCanvas";
import { useTelemetrySocket } from "./hooks/useTelemetrySocket";

const TELEMETRY_WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/api/v1/ws/telemetry`;
const MAX_REASONING_LOG_ENTRIES = 30;

export function App() {
  const { latestEvent, status } = useTelemetrySocket(TELEMETRY_WS_URL);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [reasoningLog, setReasoningLog] = useState<string[]>([]);

  const agents = useMemo(() => latestEvent?.agents ?? [], [latestEvent]);
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.agent_id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );

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

  useEffect(() => {
    setReasoningLog([]);
  }, [selectedAgentId]);

  return (
    <div className="min-h-screen bg-enclave-bg p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold tracking-wide text-slate-100">
            The Autonomous Enclave
          </h1>
          <p className="text-xs text-slate-500">Modo Dios — Silicon Polis</p>
        </div>
        <span
          className={
            status === "open"
              ? "text-xs text-enclave-accent"
              : "text-xs text-enclave-warn animate-pulse"
          }
        >
          {status === "open" ? "conectado" : "conectando…"}
        </span>
      </header>

      <main className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <GameCanvas agents={agents} onSelectAgent={setSelectedAgentId} />
          <EconomyPanel indicators={latestEvent?.indicators ?? null} tick={latestEvent?.tick ?? 0} />
        </div>
        <aside className="space-y-6">
          <ConsciousnessInspector agent={selectedAgent} reasoningLog={reasoningLog} />
          <DivineConsole selectedAgentId={selectedAgentId} />
        </aside>
      </main>
    </div>
  );
}
