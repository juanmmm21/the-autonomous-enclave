# CLAUDE.md - Estándares Técnicos de the-autonomous-enclave

Este archivo contiene los requisitos técnicos y convenciones de código específicas de **the-autonomous-enclave**. Cualquier LLM asistente debe leer y aplicar estas reglas de forma estricta antes de escribir código. Complementa a `AGENTS.md`. La visión funcional completa vive en `docs/vision.md`.

---

## 1. Stack y Arquitectura

*   **Backend:** `FastAPI` (Python 3.11+) como orquestador del ecosistema: tick engine, agentes, economía, juez autónomo y API/WebSocket. Tipado estricto con Pydantic v2.
*   **Frontend:** `React` + `TypeScript` + `Vite` + `Tailwind`. Renderizado del mapa con `Phaser 3` embebido en un componente React. Tipado estricto, sin `any` salvo justificación explícita en comentario.
*   **Broker de mensajería:** Redis (pub/sub) para la bandeja de entrada de cada agente y el tablón de ofertas del mercado.
*   **Memoria vectorial:** Qdrant para los "Vector Packs" de experiencia comprimida tras el ciclo de sueño.
*   **LLM local:** Ollama vía HTTP como backend de inferencia por defecto; el cliente se define contra un `Protocol` (`LLMBackend`) para poder sustituirlo sin tocar el resto del sistema.
*   **Contrato de API estable:** endpoints versionados (`/api/v1/...`).
*   **Precisión numérica:** balances en SimCoin y cualquier magnitud financiera usan `Decimal` en Python y se exponen como `string` en la API — nunca `float` binario. `float` solo se permite en indicadores estadísticos agregados (Gini, inflación) donde la velocidad vectorial prima sobre la precisión al céntimo.

## 2. Convenciones de Código

*   Backend: type hints obligatorios en toda función/clase pública, `async def` para I/O (LLM, Redis, Qdrant, WebSocket), `ruff` (format + lint) y `mypy --strict`.
*   Frontend: componentes funcionales, hooks, sin lógica de negocio pesada en componentes de presentación (esa lógica vive en `hooks/` o se resuelve en el backend).
*   Manejo de errores explícito en ambos lados: la API devuelve códigos y payloads de error consistentes; el frontend los maneja sin fallos silenciosos. Nunca `except: pass` ni `catch {}` vacíos.
*   Las interfaces de dominio (`Protocol` en `protocols.py`) se definen antes que las implementaciones concretas, y las implementaciones concretas (Ollama, Redis, Qdrant) son intercambiables tras esa interfaz.

## 3. Estructura Estándar

```text
the-autonomous-enclave/
├── README.md
├── docs/
│   └── vision.md              # documento de visión original del proyecto
├── backend/
│   ├── pyproject.toml
│   ├── src/enclave/
│   │   ├── models.py          # tipos de dominio (Agent, Contract, Transaction, MarketOffer...)
│   │   ├── protocols.py       # interfaces: LLMBackend, MemoryStore, MessageBroker
│   │   ├── config.py          # Settings (pydantic-settings)
│   │   ├── services/
│   │   │   ├── llm_client.py      # OllamaLLMBackend
│   │   │   ├── message_broker.py  # RedisMessageBroker
│   │   │   ├── memory_store.py    # QdrantMemoryStore
│   │   │   ├── economy.py         # Banco Central: balances, coste pasivo, bancarrota
│   │   │   ├── agent_runtime.py   # ciclo perceive/think/act de un agente
│   │   │   ├── tick_engine.py     # reloj global, orquesta a todos los agentes
│   │   │   └── judge.py           # Agente Juez: resuelve disputas contractuales
│   │   ├── api/v1/
│   │   │   ├── router.py      # endpoints REST
│   │   │   └── websocket.py   # telemetría en tiempo real
│   │   └── main.py            # FastAPI app factory
│   └── tests/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── components/
        │   ├── phaser/        # GameCanvas.tsx + MainScene.ts (mapa pixel-art)
        │   └── dashboard/     # EconomyPanel, ConsciousnessInspector, DivineConsole
        ├── hooks/              # useTelemetrySocket.ts (WebSocket)
        └── types/api.ts        # contrato compartido con el backend
```

## 4. Desarrollo Local

```bash
# Infraestructura (Redis + Qdrant)
docker compose up -d

# Backend
cd backend && uvicorn enclave.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev   # http://localhost:5173
```

## 5. Testing

```bash
# Backend
cd backend && pytest && ruff check . && mypy --strict src/

# Frontend
cd frontend && npm run typecheck
```
