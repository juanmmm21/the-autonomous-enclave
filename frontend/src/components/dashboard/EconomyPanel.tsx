import type { EconomicIndicators } from "../../types/api";

interface EconomyPanelProps {
  indicators: EconomicIndicators | null;
}

interface StatTileProps {
  label: string;
  value: string;
  unit?: string;
}

function StatTile({ label, value, unit }: StatTileProps) {
  return (
    <div className="rounded border border-enclave-edge bg-enclave-inset px-3.5 py-3 transition-colors hover:border-enclave-edge-bright">
      <p className="micro-label">{label}</p>
      <p className="mt-2 text-xl font-semibold leading-none text-enclave-ink">
        {value}
        {unit && (
          <span className="ml-1 text-[11px] font-medium tracking-wide text-enclave-ink-dim">
            {unit}
          </span>
        )}
      </p>
    </div>
  );
}

export function EconomyPanel({ indicators }: EconomyPanelProps) {
  return (
    <section className="panel">
      <header className="flex items-center justify-between border-b border-enclave-edge px-4 py-2">
        <h2 className="micro-label text-enclave-ink-mid">Telemetría macroeconómica</h2>
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            indicators ? "bg-enclave-accent shadow-glow" : "bg-enclave-edge-bright"
          }`}
          title={indicators ? "recibiendo datos" : "sin datos"}
        />
      </header>
      <div className="grid grid-cols-2 gap-2.5 p-3 xl:grid-cols-4">
        <StatTile
          label="Índice de Gini"
          value={indicators ? indicators.gini_index.toFixed(3) : "—"}
        />
        <StatTile
          label="Inflación"
          value={indicators ? (indicators.inflation_rate * 100).toFixed(1) : "—"}
          unit={indicators ? "%" : undefined}
        />
        <StatTile
          label="PIB virtual"
          value={indicators ? indicators.virtual_gdp.toFixed(2) : "—"}
          unit={indicators ? "SC" : undefined}
        />
        <StatTile
          label="Transacciones"
          value={indicators ? indicators.transactions_per_minute.toFixed(1) : "—"}
          unit={indicators ? "/min" : undefined}
        />
      </div>
    </section>
  );
}
