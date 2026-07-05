# The Autonomous Enclave (Silicon Polis)

A fully local social and macroeconomic simulation ecosystem: LLM-driven digital citizens that perceive, reason and act under computational scarcity, while a "God Observer" watches over the colony through a real-time pixel-art web interface.

## What it is and what problem it solves

The Autonomous Enclave is not a game with prewired decision trees: it's a laboratory for emergent synthetic cognition. Each citizen is an instance of an LLM (local, via Ollama) with its own personality, inventory and balance in **SimCoin**. On every *tick* of the global clock, the agent runs a closed **Perceive → Think → Act** loop: it checks its inbox and the market, invokes the model with its personality and perceived context, and translates the response (structured, schema-validated JSON) into movement, transfers, contracts or messages.

The underlying question the project explores is what social and economic dynamics emerge — cooperation, fraud, inequality, collapse — when agents with their own goals and limited resources have to coexist without a script. The "God Observer" can intervene directly on the economy (devalue the currency, subsidize agents, cut off their inference access) and watch how the system adapts or collapses.

## Goal / skills demonstrated

- **Orchestrating multiple stateful LLM agents**: each citizen keeps its personality, memory and inventory across ticks, with a strict JSON output contract validated against a schema (`AgentAction`) before any effect is applied to the world.
- **Interfaces designed before implementation**: the `Protocol`s in `protocols.py` (`LLMBackend`, `JudgeBackend`, `MemoryStore`, `MessageBroker`, `TrustLedger`) separate domain logic from concrete backends (Ollama, Redis, Qdrant), so any of them can be swapped without touching the rest of the system.
- **Financial precision**: the entire economic ledger uses `Decimal` in the backend and serializes as `string` over the API, avoiding the binary rounding errors typical of using `float` for money.
- **End-to-end real-time architecture**: an async `TickEngine` runs in the background inside FastAPI's lifespan and broadcasts every tick to all connected WebSocket clients through a subscriber hub, consumed on the frontend by a Phaser map and React panels that resync without a page reload.
- **Evidence-grounded dispute resolution by a second LLM**: the Judge Agent cites the real transaction history between the two parties (not just the contract terms) when arbitrating a breach, uses a higher-capacity reasoning model to decide who's at fault, applies the fine on the central bank, and docks the injured party's trust in the offender — verified live against a real `phi4` judge with a crafted advance-payment dispute.
- **Real memory compression cycle**: at the end of every simulated day, each agent's tick-by-tick reasoning is summarized, embedded and persisted in Qdrant, then retrieved as relevant past memories on future perceives — verified live against a running Ollama + Qdrant stack, not just unit-tested.
- **Macro indicators derived from real state, not placeholders**: the simulated energy price evolves every tick (scarcity drift plus a periodic oscillation) and feeds a real day-over-day inflation figure; transactions-per-minute is computed from the central bank's actual transaction ledger over a real-time window, not a hardcoded `0.0`.

## How it works

1. The **Central Bank** (`CentralBank`) opens a SimCoin account for every agent registered on the `TickEngine`.
2. On every tick, the `TickEngine` walks through the living agents and, for each one, the `AgentRuntime` runs:
   - **Perceive**: fetches its inbox (Redis), the open market offers, and its most relevant past-day memories (Qdrant).
   - **Think**: invokes the local LLM (Ollama) with its personality and perceived context, requiring a JSON response validated against `AgentAction`.
   - **Act**: applies the corresponding effect (move, send a message, post an offer, transfer SimCoin, sign a contract, file a dispute, sleep, or do nothing).
3. The tick's **passive cost** (computational upkeep) is charged; if the balance reaches zero, the agent goes bankrupt.
4. Contracts marked as `DISPUTED` are resolved asynchronously by the **Judge Agent**, which reviews the real transaction history between the two parties, fines whoever is at fault, and docks the injured party's trust in the offender.
5. Every `ticks_per_day` ticks, the **sleep cycle** runs: each agent's accumulated reasoning for the day is summarized and persisted as an embedding in Qdrant, and the intermediate log is cleared for the next day.
6. At the end of every tick, a `TickEvent` (snapshot of all agents + macro indicators) is broadcast over WebSocket to the web interface, which updates the Phaser map and the telemetry panels in real time.
7. The "God Observer" can intervene at any moment from the **Divine Intervention Console**: devalue the currency, subsidize an agent, or cut its inference quota (technological blackout).

## Architecture

```text
the-autonomous-enclave/
├── docs/vision.md              # original project vision document
├── docker-compose.yml          # Redis (broker) + Qdrant (vector memory) for local development
├── backend/
│   ├── pyproject.toml
│   ├── src/enclave/
│   │   ├── models.py           # domain: AgentState, MarketOffer, Contract, Transaction, TickEvent...
│   │   ├── protocols.py        # interfaces: LLMBackend, JudgeBackend, MemoryStore, MessageBroker, TrustLedger
│   │   ├── exceptions.py       # domain errors (insufficient funds, breached contract...)
│   │   ├── config.py           # Settings from environment variables
│   │   ├── seed.py             # initial citizen population (personalities, system prompts, positions)
│   │   ├── services/
│   │   │   ├── llm_client.py       # OllamaLLMBackend / OllamaJudgeBackend
│   │   │   ├── message_broker.py   # RedisMessageBroker (private inbox + market board)
│   │   │   ├── memory_store.py     # QdrantMemoryStore (sleep cycle / memory compression)
│   │   │   ├── economy.py          # CentralBank: balances, ledger, passive cost, devaluation, subsidies
│   │   │   ├── contracts.py        # ContractRegistry
│   │   │   ├── agent_runtime.py    # a single agent's Perceive/Think/Act cycle
│   │   │   ├── tick_engine.py      # global clock, orchestrates every agent, the sleep cycle and trust
│   │   │   └── judge.py            # Judge Agent: resolves disputed contracts using real transaction evidence
│   │   ├── api/v1/
│   │   │   ├── router.py           # /health, /agents, /tick
│   │   │   ├── interventions.py    # /interventions/devalue|subsidize|blackout
│   │   │   └── websocket.py        # /ws/telemetry + TelemetryHub
│   │   └── main.py             # FastAPI app factory + lifespan (seeds citizens, starts the TickEngine)
│   └── tests/                  # pytest: economy, models, agent cycle, tick engine, seeding
└── frontend/
    └── src/
        ├── components/
        │   ├── phaser/          # GameCanvas.tsx + MainScene.ts (pixel-art map, agent selection)
        │   └── dashboard/       # EconomyPanel, ConsciousnessInspector, DivineConsole
        ├── hooks/useTelemetrySocket.ts  # WebSocket with automatic reconnection
        └── types/api.ts         # contract shared with the backend
```

## Requirements and installation

- Python 3.11+
- Node.js 20+
- Docker (for Redis and Qdrant)
- [Ollama](https://ollama.com) running locally, with at least one model pulled (e.g. `ollama pull llama3.2`)

```bash
# Infrastructure
docker compose up -d

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # adjust models/URLs if your setup differs from the defaults

# Frontend
cd ../frontend
npm install
```

## Usage

```bash
# Backend (port 8000)
cd backend && source .venv/bin/activate
uvicorn enclave.main:app --reload --port 8000

# Frontend (port 5173, proxies /api to localhost:8000)
cd frontend && npm run dev
```

With both running, `http://localhost:5173` shows "God Mode": the Phaser map with the five seeded citizens (Ada, Boris, Clio, Dorian, Elena — each with a distinct personality), the economic indicators panel and, once you select an agent, its Consciousness Inspector with inventory, trust links and a live reasoning feed.

## API contract

All endpoints live under `/api/v1`. Financial amounts (`balance`, `unit_price`, `amount`, `penalty`) are exposed as `string` to preserve decimal precision.

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/agents` | Snapshot of every registered agent |
| `GET` | `/agents/{agent_id}` | Snapshot of one agent (404 if it doesn't exist) |
| `GET` | `/tick` | Current tick of the global clock |
| `POST` | `/interventions/devalue` | `{"factor": "0.5"}` — devalues every citizen's SimCoin |
| `POST` | `/interventions/subsidize` | `{"agent_id": "...", "amount": "100"}` — prints SimCoin for an agent |
| `POST` | `/interventions/blackout` | `{"agent_id": "...", "quota": 0}` — adjusts an agent's inference quota |
| `WS` | `/ws/telemetry` | Streams `TickEvent` (agent snapshot + macro indicators) on every tick |

## Development

```bash
# Backend
cd backend && source .venv/bin/activate
pytest
ruff check .
mypy --strict src/

# Frontend
cd frontend
npm run typecheck
npm run lint
npm run build
```

## Troubleshooting

- **The telemetry WebSocket won't connect**: check that the backend is running on the port `vite.config.ts` expects (`8000` by default), and that nothing else is bound to `5173` or `8000`.
- **`OllamaLLMBackend` raises `LLMGenerationError`**: Ollama isn't running, the configured model (`ENCLAVE_OLLAMA_MODEL`) hasn't been pulled, or the model isn't returning valid JSON despite `format: "json"` — check the backend log, which includes the raw text the model returned. This is expected occasionally with smaller local models (e.g. llama3.2 sometimes deviates from the exact action schema); the tick engine logs it and moves on to the next agent instead of crashing.
- **An agent's position looks wrong on the map**: `Position` enforces `0 <= x < GRID_WIDTH` and `0 <= y < GRID_HEIGHT` (must match `GRID_WIDTH`/`GRID_HEIGHT` in `frontend/src/components/phaser/MainScene.ts`); a move outside those bounds is rejected as a malformed action rather than silently accepted.
- **Qdrant logs version-compatibility warnings**: informational notice from `qdrant-client` when it can't verify the server version; it doesn't block startup.
- **`mypy --strict` fails on `numpy` stubs**: `numpy` arrives as a transitive dependency of `qdrant-client`; `pyproject.toml` pins `python_version = "3.12"` in the mypy config specifically to avoid a syntax conflict between its stubs and strict mode.

## Roadmap

- Auction inference quotas between agents (`inference_quota` exists on the model but isn't yet auctioned or actively consumed in the tick loop).
- Persist the economic ledger in Postgres so it survives process restarts (today it lives in memory inside `CentralBank`).
- Real pixel-art tileset for the Phaser map (today the citizens are code-generated geometric markers).
- Auto-file disputes: today an agent must choose `FILE_DISPUTE` itself; a wronged agent that just goes quiet never reaches the Judge.
- Let the Divine Console perturb the energy price directly (today it only moves SimCoin balances and inference quotas).

## License

MIT — see [LICENSE](LICENSE).
