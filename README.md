# The Autonomous Enclave (Silicon Polis)

Un ecosistema de simulación social y macroeconómica local: ciudadanos digitales impulsados por LLMs que perciben, razonan y actúan bajo escasez computacional, mientras un "Dios Observador" supervisa la colonia desde una interfaz web pixel-art en tiempo real.

## Qué es y qué problema resuelve

The Autonomous Enclave no es un juego con árboles de decisión prefijados: es un laboratorio de cognición sintética emergente. Cada ciudadano es una instancia de un LLM (local, vía Ollama) con una personalidad propia, un inventario y un balance en **SimCoin**. En cada *tick* del reloj global, el agente ejecuta un ciclo cerrado **Perceive → Think → Act**: revisa su bandeja de entrada y el mercado, invoca al modelo con su contexto y personalidad, y traduce la respuesta (JSON estructurado y validado) en movimientos, transferencias, contratos o mensajes.

El problema de fondo que explora el proyecto es qué dinámicas sociales y económicas emergen —cooperación, fraude, desigualdad, colapso— cuando agentes con objetivos propios y recursos limitados deben coexistir sin guion. El "Dios Observador" puede intervenir directamente sobre la economía (devaluar la moneda, subvencionar agentes, cortar su acceso a inferencia) y observar cómo el sistema se adapta o colapsa.

## Objetivo / habilidades demostradas

- **Orquestación de múltiples agentes LLM con estado persistente**: cada ciudadano mantiene personalidad, memoria e inventario a través de ticks, con un contrato de salida JSON estricto validado contra un esquema (`AgentAction`) antes de aplicar ningún efecto sobre el mundo.
- **Diseño de interfaces antes que implementación**: los `Protocol` de `protocols.py` (`LLMBackend`, `JudgeBackend`, `MemoryStore`, `MessageBroker`) separan la lógica de dominio de los backends concretos (Ollama, Redis, Qdrant), permitiendo sustituir cualquiera de ellos sin tocar el resto del sistema.
- **Precisión financiera**: todo el ledger económico usa `Decimal` en el backend y se serializa como `string` en la API, evitando errores de redondeo binario típicos de usar `float` para dinero.
- **Arquitectura tiempo real de extremo a extremo**: un `TickEngine` asíncrono corre en segundo plano dentro del lifespan de FastAPI y difunde cada tick a todos los clientes WebSocket conectados a través de un hub de suscriptores, consumido en el frontend por un mapa Phaser y paneles React que se re-sincronizan sin recargar la página.
- **Resolución de disputas por un segundo LLM**: el Agente Juez usa un modelo de mayor capacidad de razonamiento para arbitrar contratos incumplidos y ejecutar multas directamente sobre el banco central, de forma completamente asíncrona respecto al ciclo de los ciudadanos.

## Cómo funciona

1. El **Banco Central** (`CentralBank`) abre una cuenta en SimCoin para cada agente registrado en el `TickEngine`.
2. En cada tick, el `TickEngine` recorre a los agentes vivos y, para cada uno, el `AgentRuntime` ejecuta:
   - **Perceive**: obtiene su bandeja de entrada (Redis) y las ofertas abiertas del mercado.
   - **Think**: invoca al LLM local (Ollama) con su personalidad y contexto percibido, exigiendo una respuesta JSON validada contra `AgentAction`.
   - **Act**: aplica el efecto correspondiente (mover, enviar mensaje, publicar oferta, transferir SimCoin, firmar contrato, denunciar disputa, dormir o no hacer nada).
3. Se cobra el **coste pasivo** del tick (mantenimiento computacional); si el balance llega a cero, el agente queda en bancarrota.
4. Los contratos marcados como `DISPUTED` se resuelven de forma asíncrona por el **Agente Juez**, que aplica una multa al responsable.
5. Al final de cada tick se emite un `TickEvent` (snapshot de todos los agentes + indicadores macro) por WebSocket a la interfaz web, que actualiza el mapa Phaser y los paneles de telemetría en tiempo real.
6. El "Dios Observador" puede intervenir en cualquier momento desde la **Consola de Intervención Divina**: devaluar la moneda, subvencionar a un agente o cortarle su cuota de inferencia (apagón tecnológico).

## Arquitectura

```text
the-autonomous-enclave/
├── docs/vision.md              # documento de visión original del proyecto
├── docker-compose.yml          # Redis (broker) + Qdrant (memoria vectorial) para desarrollo local
├── backend/
│   ├── pyproject.toml
│   ├── src/enclave/
│   │   ├── models.py           # dominio: AgentState, MarketOffer, Contract, Transaction, TickEvent...
│   │   ├── protocols.py        # interfaces: LLMBackend, JudgeBackend, MemoryStore, MessageBroker
│   │   ├── exceptions.py       # errores de dominio (fondos insuficientes, contrato incumplido...)
│   │   ├── config.py           # Settings vía variables de entorno
│   │   ├── services/
│   │   │   ├── llm_client.py       # OllamaLLMBackend / OllamaJudgeBackend
│   │   │   ├── message_broker.py   # RedisMessageBroker (inbox privado + tablón de mercado)
│   │   │   ├── memory_store.py     # QdrantMemoryStore (ciclo de sueño / compresión de memoria)
│   │   │   ├── economy.py          # CentralBank: balances, coste pasivo, devaluación, subsidios
│   │   │   ├── contracts.py        # ContractRegistry
│   │   │   ├── agent_runtime.py    # ciclo Perceive/Think/Act de un agente
│   │   │   ├── tick_engine.py      # reloj global, orquesta a todos los agentes
│   │   │   └── judge.py            # Agente Juez: resuelve contratos en disputa
│   │   ├── api/v1/
│   │   │   ├── router.py           # /health, /agents, /tick
│   │   │   ├── interventions.py    # /interventions/devalue|subsidize|blackout
│   │   │   └── websocket.py        # /ws/telemetry + TelemetryHub
│   │   └── main.py             # FastAPI app factory + lifespan (arranca el TickEngine)
│   └── tests/                  # pytest: economía, modelos, ciclo de agente
└── frontend/
    └── src/
        ├── components/
        │   ├── phaser/          # GameCanvas.tsx + MainScene.ts (mapa pixel-art, selección de agentes)
        │   └── dashboard/       # EconomyPanel, ConsciousnessInspector, DivineConsole
        ├── hooks/useTelemetrySocket.ts  # WebSocket con reconexión automática
        └── types/api.ts         # contrato compartido con el backend
```

## Requisitos e instalación

- Python 3.11+
- Node.js 20+
- Docker (para Redis y Qdrant)
- [Ollama](https://ollama.com) corriendo en local, con al menos un modelo descargado (p. ej. `ollama pull llama3.2`)

```bash
# Infraestructura
docker compose up -d

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # ajusta modelos/URLs si tu setup difiere del default

# Frontend
cd ../frontend
npm install
```

## Uso

```bash
# Backend (puerto 8000)
cd backend && source .venv/bin/activate
uvicorn enclave.main:app --reload --port 8000

# Frontend (puerto 5173, con proxy a /api hacia localhost:8000)
cd frontend && npm run dev
```

Con ambos corriendo, `http://localhost:5173` muestra el "Modo Dios": el mapa Phaser, el panel de indicadores económicos y, al seleccionar un agente, su Inspector de Conciencia con inventario, confianza y flujo de razonamiento en vivo.

En este scaffold inicial el `TickEngine` arranca **sin ciudadanos registrados** (`GET /api/v1/agents` devuelve `[]`); el reloj corre igualmente y emite telemetría vacía. Sembrar la población inicial de agentes es el siguiente hito (ver Roadmap).

## Contrato de API

Todos los endpoints están bajo `/api/v1`. Los montos financieros (`balance`, `unit_price`, `amount`, `penalty`) se exponen como `string` para preservar precisión decimal.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Comprobación de salud |
| `GET` | `/agents` | Snapshot de todos los agentes registrados |
| `GET` | `/agents/{agent_id}` | Snapshot de un agente (404 si no existe) |
| `GET` | `/tick` | Tick actual del reloj global |
| `POST` | `/interventions/devalue` | `{"factor": "0.5"}` — devalúa el SimCoin de todos los ciudadanos |
| `POST` | `/interventions/subsidize` | `{"agent_id": "...", "amount": "100"}` — imprime SimCoin para un agente |
| `POST` | `/interventions/blackout` | `{"agent_id": "...", "quota": 0}` — ajusta la cuota de inferencia de un agente |
| `WS` | `/ws/telemetry` | Streaming de `TickEvent` (snapshot de agentes + indicadores macro) en cada tick |

## Desarrollo

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

- **El WebSocket de telemetría no conecta**: comprueba que el backend está corriendo en el puerto que espera `vite.config.ts` (por defecto `8000`), y que no hay otro proceso ocupando `5173` u `8000`.
- **`OllamaLLMBackend` lanza `LLMGenerationError`**: Ollama no está corriendo, el modelo configurado (`ENCLAVE_OLLAMA_MODEL`) no está descargado, o el modelo no está devolviendo JSON válido pese al `format: "json"` — revisa el log del backend, que incluye el texto crudo devuelto por el modelo.
- **Qdrant lanza warnings de compatibilidad de versión**: es un aviso informativo del cliente (`qdrant-client`) al no poder verificar la versión del servidor; no bloquea el arranque.
- **`mypy --strict` falla sobre stubs de `numpy`**: `numpy` llega como dependencia transitiva de `qdrant-client`; el `pyproject.toml` fija `python_version = "3.12"` en la config de mypy precisamente para evitar el conflicto de sintaxis de sus stubs con el modo estricto.

## Roadmap

- Sembrar una población inicial de ciudadanos (personalidades, prompts de sistema, posiciones de partida) al arrancar el `TickEngine`.
- Ciclo de sueño real: al final de cada jornada simulada, resumir las interacciones del día y persistirlas en Qdrant vía `QdrantMemoryStore.store_daily_summary`, vaciando la memoria intermedia inyectada en el prompt.
- Auctioning de cuotas de inferencia entre agentes (hoy `inference_quota` existe en el modelo pero no se subasta ni se consume activamente en el bucle de tick).
- Persistencia del ledger económico en Postgres para sobrevivir a reinicios del proceso (hoy vive en memoria en `CentralBank`).
- Tileset pixel-art real para el mapa Phaser (hoy son marcadores geométricos generados por código).
- Métricas de inflación y transacciones por minuto en `EconomicIndicators` (hoy están cableadas a `0.0` a la espera de una serie temporal de precios/transacciones).

## Licencia

MIT — ver [LICENSE](LICENSE).
