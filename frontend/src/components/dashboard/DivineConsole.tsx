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

  const buttonClasses =
    "rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:border-enclave-accent hover:text-enclave-accent disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <section className="space-y-2 rounded-lg border border-enclave-warn/40 bg-enclave-panel p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-enclave-warn">
        Consola de Intervención Divina
      </h2>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={state === "pending"}
          className={buttonClasses}
          onClick={() => run(() => postIntervention("devalue", { factor: 0.5 }))}
        >
          Devaluar SimCoin 50%
        </button>
        <button
          type="button"
          disabled={state === "pending" || !selectedAgentId}
          className={buttonClasses}
          onClick={() =>
            run(() => postIntervention("blackout", { agent_id: selectedAgentId, quota: 0 }))
          }
        >
          Apagón de inferencia
        </button>
        <button
          type="button"
          disabled={state === "pending" || !selectedAgentId}
          className={buttonClasses}
          onClick={() =>
            run(() =>
              postIntervention("subsidize", { agent_id: selectedAgentId, amount: 100 }),
            )
          }
        >
          Subvencionar (+100)
        </button>
      </div>
      {!selectedAgentId && (
        <p className="text-xs text-slate-500">
          Selecciona un agente en el mapa para el apagón o la subvención.
        </p>
      )}
      {lastError && <p className="text-xs text-enclave-danger">{lastError}</p>}
    </section>
  );
}
