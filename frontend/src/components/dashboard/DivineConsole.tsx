import { useState } from "react";

interface DivineConsoleProps {
  selectedAgentId: string | null;
}

type InterventionState = "idle" | "pending" | "error";

async function postIntervention(path: string, body: Record<string, unknown>): Promise<void> {
  const response = await fetch(`/api/v1/interventions/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    // El cuerpo puede no ser JSON (p.ej. un 502 del proxy): en ese caso se
    // conserva el mensaje genérico con el status en lugar de un error de parseo.
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? `intervention '${path}' failed with ${response.status}`);
  }
}

interface InterventionButtonProps {
  label: string;
  effect: string;
  disabled: boolean;
  onClick: () => void;
}

function InterventionButton({ label, effect, disabled, onClick }: InterventionButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="group flex w-full items-center justify-between gap-3 rounded border border-enclave-edge bg-enclave-inset px-3 py-2 text-left text-xs font-medium text-enclave-ink-mid transition-colors hover:border-enclave-warn/50 hover:text-enclave-ink active:translate-y-px disabled:pointer-events-none disabled:opacity-40"
    >
      <span>{label}</span>
      <span className="shrink-0 rounded-sm border border-enclave-edge bg-enclave-bg px-1.5 py-0.5 text-[10px] tabular-nums text-enclave-ink-dim transition-colors group-hover:border-enclave-warn/40 group-hover:text-enclave-warn">
        {effect}
      </span>
    </button>
  );
}

export function DivineConsole({ selectedAgentId }: DivineConsoleProps) {
  const [state, setState] = useState<InterventionState>("idle");
  const [lastError, setLastError] = useState<string | null>(null);

  const run = async (action: () => Promise<void>): Promise<void> => {
    setState("pending");
    setLastError(null);
    try {
      await action();
      setState("idle");
    } catch (error) {
      setState("error");
      setLastError(error instanceof Error ? error.message : "intervención desconocida fallida");
    }
  };

  return (
    <section className="panel overflow-hidden">
      <header className="flex items-center gap-2.5 border-b border-enclave-warn/25 bg-enclave-warn/5 px-4 py-2.5">
        <span
          aria-hidden="true"
          className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-enclave-warn/50 text-[10px] font-bold leading-none text-enclave-warn"
        >
          !
        </span>
        <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-enclave-warn">
          Consola de Intervención Divina
        </h2>
      </header>

      <div className="flex flex-col gap-1.5 p-3">
        <InterventionButton
          label="Devaluar SimCoin"
          effect="×0.5"
          disabled={state === "pending"}
          onClick={() => void run(() => postIntervention("devalue", { factor: 0.5 }))}
        />
        <InterventionButton
          label="Apagón de inferencia"
          effect="quota=0"
          disabled={state === "pending" || !selectedAgentId}
          onClick={() =>
            void run(() => postIntervention("blackout", { agent_id: selectedAgentId, quota: 0 }))
          }
        />
        <InterventionButton
          label="Subvencionar agente"
          effect="+100 SC"
          disabled={state === "pending" || !selectedAgentId}
          onClick={() =>
            void run(() =>
              postIntervention("subsidize", { agent_id: selectedAgentId, amount: 100 }),
            )
          }
        />
        <InterventionButton
          label="Shock energético"
          effect="×2.0"
          disabled={state === "pending"}
          onClick={() => void run(() => postIntervention("energy_shock", { factor: 2.0 }))}
        />
        <InterventionButton
          label="Abundancia energética"
          effect="×0.5"
          disabled={state === "pending"}
          onClick={() => void run(() => postIntervention("energy_shock", { factor: 0.5 }))}
        />
      </div>

      {(!selectedAgentId || lastError) && (
        <div className="space-y-1 border-t border-enclave-edge px-4 py-2.5">
          {!selectedAgentId && (
            <p className="text-[11px] leading-relaxed text-enclave-ink-dim">
              Selecciona un agente en el mapa para el apagón o la subvención.
            </p>
          )}
          {lastError && (
            <p className="text-[11px] font-medium leading-relaxed text-enclave-danger">
              ERR · {lastError}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
