import { useState } from "react";
import type { FormEvent } from "react";

import type { AgentState, Personality } from "../../types/api";

const PERSONALITY_OPTIONS: ReadonlyArray<{ value: Personality; label: string }> = [
  { value: "ambitious", label: "ambicioso" },
  { value: "cautious", label: "cauteloso" },
  { value: "cooperative", label: "cooperativo" },
  { value: "altruistic", label: "altruista" },
  { value: "machiavellian", label: "maquiavélico" },
];

type SubmitState = "idle" | "pending" | "error" | "created";

interface CreateCitizenBody {
  display_name: string;
  personality: Personality[];
  /** Decimal como string, igual que el resto de montos de la API. */
  starting_balance?: string;
}

async function postCitizen(body: CreateCitizenBody): Promise<AgentState> {
  const response = await fetch("/api/v1/citizens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    // El cuerpo puede no ser JSON (p.ej. un 502 del proxy): se conserva un
    // mensaje genérico con el status en vez de fallar el parseo.
    const payload = (await response.json().catch(() => ({}))) as { detail?: unknown };
    const detail =
      typeof payload.detail === "string"
        ? payload.detail
        : `la creación falló con HTTP ${response.status}`;
    throw new Error(detail);
  }
  return (await response.json()) as AgentState;
}

/**
 * Fundición de ciudadanos: crea un nuevo agente LLM en caliente vía
 * `POST /api/v1/citizens`. El backend lo registra en el TickEngine y difunde
 * un TickEvent inmediato, así que el recién nacido aparece en el mapa al
 * instante.
 */
export function CitizenFoundry() {
  const [displayName, setDisplayName] = useState("");
  const [traits, setTraits] = useState<Personality[]>([]);
  const [balance, setBalance] = useState("");
  const [state, setState] = useState<SubmitState>("idle");
  const [feedback, setFeedback] = useState<string | null>(null);

  const toggleTrait = (trait: Personality): void => {
    setTraits((current) =>
      current.includes(trait) ? current.filter((t) => t !== trait) : [...current, trait],
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    const trimmedName = displayName.trim();
    const trimmedBalance = balance.trim();
    if (trimmedBalance && !(Number(trimmedBalance) > 0)) {
      setState("error");
      setFeedback("el balance inicial debe ser un número positivo");
      return;
    }

    setState("pending");
    setFeedback(null);
    try {
      const body: CreateCitizenBody = { display_name: trimmedName, personality: traits };
      if (trimmedBalance) {
        body.starting_balance = trimmedBalance;
      }
      const created = await postCitizen(body);
      setState("created");
      setFeedback(`${created.display_name} (${created.agent_id}) camina ya por la ciudad`);
      setDisplayName("");
      setTraits([]);
      setBalance("");
    } catch (error) {
      setState("error");
      setFeedback(error instanceof Error ? error.message : "error desconocido al crear");
    }
  };

  const canSubmit = state !== "pending" && displayName.trim().length > 0 && traits.length > 0;

  return (
    <section className="panel overflow-hidden">
      <header className="flex items-center gap-2.5 border-b border-enclave-accent/25 bg-enclave-accent/5 px-4 py-2.5">
        <span
          aria-hidden="true"
          className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-enclave-accent/50 text-[10px] font-bold leading-none text-enclave-accent"
        >
          +
        </span>
        <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-enclave-accent">
          Fundición de ciudadanos
        </h2>
      </header>

      <form className="flex flex-col gap-3 p-3" onSubmit={(event) => void handleSubmit(event)}>
        <label className="flex flex-col gap-1">
          <span className="micro-label">Nombre</span>
          <input
            type="text"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            maxLength={40}
            placeholder="p.ej. Marta"
            disabled={state === "pending"}
            className="rounded border border-enclave-edge bg-enclave-inset px-2.5 py-1.5 text-xs text-enclave-ink placeholder:text-enclave-ink-dim focus:border-enclave-accent/50 focus:outline-none disabled:opacity-50"
          />
        </label>

        <fieldset className="flex flex-col gap-1" disabled={state === "pending"}>
          <legend className="micro-label mb-1">Personalidad (mínimo 1)</legend>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {PERSONALITY_OPTIONS.map((option) => (
              <label
                key={option.value}
                className="flex cursor-pointer items-center gap-1.5 text-xs text-enclave-ink-mid transition-colors hover:text-enclave-ink"
              >
                <input
                  type="checkbox"
                  checked={traits.includes(option.value)}
                  onChange={() => toggleTrait(option.value)}
                  className="h-3 w-3 accent-teal-400"
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <label className="flex flex-col gap-1">
          <span className="micro-label">Balance inicial (opcional, por defecto 120 SC)</span>
          <input
            type="number"
            value={balance}
            onChange={(event) => setBalance(event.target.value)}
            min="1"
            step="any"
            placeholder="120"
            disabled={state === "pending"}
            className="rounded border border-enclave-edge bg-enclave-inset px-2.5 py-1.5 text-xs text-enclave-ink placeholder:text-enclave-ink-dim focus:border-enclave-accent/50 focus:outline-none disabled:opacity-50"
          />
        </label>

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded border border-enclave-accent/40 bg-enclave-accent/10 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-enclave-accent transition-colors hover:bg-enclave-accent/20 active:translate-y-px disabled:pointer-events-none disabled:opacity-40"
        >
          {state === "pending" ? "Creando…" : "Dar vida al ciudadano"}
        </button>
      </form>

      {feedback && (
        <div className="border-t border-enclave-edge px-4 py-2.5">
          <p
            className={`text-[11px] font-medium leading-relaxed ${
              state === "error" ? "text-enclave-danger" : "text-enclave-accent"
            }`}
          >
            {state === "error" ? "ERR · " : "OK · "}
            {feedback}
          </p>
        </div>
      )}
    </section>
  );
}
