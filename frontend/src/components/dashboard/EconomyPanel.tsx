import type { EconomicIndicators } from "../../types/api";

interface EconomyPanelProps {
  indicators: EconomicIndicators | null;
  tick: number;
}

interface StatTileProps {
  label: string;
  value: string;
}

function StatTile({ label, value }: StatTileProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-enclave-panel p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-xl font-semibold text-enclave-accent">{value}</p>
    </div>
  );
}

export function EconomyPanel({ indicators, tick }: EconomyPanelProps) {
  return (
    <section className="space-y-3">
      <header className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
          Telemetría macroeconómica
        </h2>
        <span className="text-xs text-slate-500">tick {tick}</span>
      </header>
      <div className="grid grid-cols-2 gap-3">
        <StatTile
          label="Índice de Gini"
          value={indicators ? indicators.gini_index.toFixed(3) : "—"}
        />
        <StatTile
          label="Inflación"
          value={indicators ? `${(indicators.inflation_rate * 100).toFixed(1)}%` : "—"}
        />
        <StatTile
          label="PIB virtual"
          value={indicators ? indicators.virtual_gdp.toFixed(2) : "—"}
        />
        <StatTile
          label="Tx / minuto"
          value={indicators ? indicators.transactions_per_minute.toFixed(1) : "—"}
        />
      </div>
    </section>
  );
}
