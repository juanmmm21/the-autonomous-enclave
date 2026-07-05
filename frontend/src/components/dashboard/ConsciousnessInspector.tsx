import type { AgentState } from "../../types/api";

interface ConsciousnessInspectorProps {
  agent: AgentState | null;
  reasoningLog: string[];
}

export function ConsciousnessInspector({ agent, reasoningLog }: ConsciousnessInspectorProps) {
  if (!agent) {
    return (
      <section className="rounded-lg border border-slate-800 bg-enclave-panel p-4 text-sm text-slate-500">
        Selecciona un ciudadano en el mapa para inspeccionar su conciencia.
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-enclave-panel p-4">
      <header>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
          {agent.display_name}
        </h2>
        <p className="text-xs text-slate-500">
          {agent.agent_id} · {agent.status} · {agent.personality.join(", ")}
        </p>
      </header>

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-slate-500">Balance</dt>
        <dd className="text-right text-enclave-accent">{agent.balance} SimCoin</dd>
        <dt className="text-slate-500">Cuota de inferencia</dt>
        <dd className="text-right">{agent.inference_quota}</dd>
      </dl>

      <div>
        <h3 className="text-xs uppercase tracking-wide text-slate-500">Inventario</h3>
        {Object.keys(agent.inventory).length === 0 ? (
          <p className="text-sm text-slate-600">Sin activos.</p>
        ) : (
          <ul className="text-sm">
            {Object.entries(agent.inventory).map(([assetType, quantity]) => (
              <li key={assetType} className="flex justify-between">
                <span>{assetType}</span>
                <span>{quantity}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="text-xs uppercase tracking-wide text-slate-500">Confianza</h3>
        {Object.keys(agent.trust_links).length === 0 ? (
          <p className="text-sm text-slate-600">Sin conexiones registradas.</p>
        ) : (
          <ul className="text-sm">
            {Object.entries(agent.trust_links).map(([peerId, score]) => (
              <li key={peerId} className="flex justify-between">
                <span>{peerId}</span>
                <span>{score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="text-xs uppercase tracking-wide text-slate-500">
          Flujo de pensamiento
        </h3>
        <div className="mt-1 max-h-40 space-y-1 overflow-y-auto rounded border border-slate-800 bg-black/30 p-2 font-mono text-xs text-slate-300">
          {reasoningLog.length === 0 ? (
            <p className="text-slate-600">Aún no hay razonamiento registrado.</p>
          ) : (
            reasoningLog.map((entry, index) => <p key={index}>{entry}</p>)
          )}
        </div>
      </div>
    </section>
  );
}
