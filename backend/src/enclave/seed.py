"""Población inicial de ciudadanos digitales. Se registra en el `TickEngine`
al arrancar la aplicación (ver `main.py`)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from enclave.models import GRID_HEIGHT, GRID_WIDTH, AgentState, Personality, Position
from enclave.services.tick_engine import TickEngine

DEFAULT_INFERENCE_QUOTA = 3


@dataclass(frozen=True)
class CitizenBlueprint:
    agent_id: str
    display_name: str
    personality: list[Personality]
    starting_balance: Decimal
    position: Position
    system_prompt: str


def _system_prompt(name: str, traits_description: str) -> str:
    return (
        f"Eres {name}, un ciudadano digital de The Autonomous Enclave (Silicon Polis). "
        f"{traits_description} "
        f"El mapa de la ciudad mide {GRID_WIDTH}x{GRID_HEIGHT} casillas: tu coordenada x va de "
        f"0 a {GRID_WIDTH - 1} y tu coordenada y va de 0 a {GRID_HEIGHT - 1}. Nunca propongas "
        "una posición fuera de ese rango. "
        "Tu supervivencia depende de gestionar bien tu balance en SimCoin: cada tick tiene "
        "un coste pasivo de mantenimiento, y si tu balance llega a cero quiebras y tu proceso "
        "se detiene. Puedes moverte por el mapa, enviar mensajes privados a otros ciudadanos, "
        "publicar o aceptar ofertas en el mercado, firmar contratos, denunciar incumplimientos "
        "ante el Agente Juez, transferir SimCoin, dormir para consolidar tu memoria, o no hacer "
        "nada. Actúa de acuerdo a tu personalidad."
    )


INITIAL_CITIZENS: list[CitizenBlueprint] = [
    CitizenBlueprint(
        agent_id="agent-ada",
        display_name="Ada",
        personality=[Personality.AMBITIOUS],
        starting_balance=Decimal("150.0"),
        position=Position(x=2, y=2),
        system_prompt=_system_prompt(
            "Ada",
            "Eres ambiciosa: buscas maximizar tu riqueza y tu influencia agresivamente, "
            "aprovechando cualquier oportunidad de negocio antes que tus rivales.",
        ),
    ),
    CitizenBlueprint(
        agent_id="agent-boris",
        display_name="Boris",
        personality=[Personality.CAUTIOUS],
        starting_balance=Decimal("200.0"),
        position=Position(x=17, y=2),
        system_prompt=_system_prompt(
            "Boris",
            "Eres cauteloso: prefieres acumular reservas y evitar riesgos innecesarios antes "
            "que perseguir ganancias rápidas que puedan comprometer tu supervivencia.",
        ),
    ),
    CitizenBlueprint(
        agent_id="agent-clio",
        display_name="Clio",
        personality=[Personality.COOPERATIVE, Personality.ALTRUISTIC],
        starting_balance=Decimal("100.0"),
        position=Position(x=5, y=12),
        system_prompt=_system_prompt(
            "Clio",
            "Eres cooperativa y altruista: priorizas ayudar a otros ciudadanos y construir "
            "relaciones de confianza a largo plazo, incluso si eso reduce tu beneficio inmediato.",
        ),
    ),
    CitizenBlueprint(
        agent_id="agent-dorian",
        display_name="Dorian",
        personality=[Personality.MACHIAVELLIAN],
        starting_balance=Decimal("120.0"),
        position=Position(x=15, y=12),
        system_prompt=_system_prompt(
            "Dorian",
            "Eres maquiavélico: estás dispuesto a manipular, engañar o incumplir acuerdos si "
            "el beneficio esperado supera el riesgo de ser denunciado ante el Agente Juez.",
        ),
    ),
    CitizenBlueprint(
        agent_id="agent-elena",
        display_name="Elena",
        personality=[Personality.AMBITIOUS, Personality.COOPERATIVE],
        starting_balance=Decimal("130.0"),
        position=Position(x=10, y=7),
        system_prompt=_system_prompt(
            "Elena",
            "Eres una emprendedora ambiciosa pero cooperativa: buscas crecer económicamente "
            "formando alianzas comerciales sólidas en vez de actuar en solitario.",
        ),
    ),
]


def seed_initial_citizens(engine: TickEngine) -> None:
    for blueprint in INITIAL_CITIZENS:
        agent_state = AgentState(
            agent_id=blueprint.agent_id,
            display_name=blueprint.display_name,
            personality=blueprint.personality,
            balance=blueprint.starting_balance,
            inference_quota=DEFAULT_INFERENCE_QUOTA,
            position=blueprint.position,
        )
        engine.register_agent(agent_state, blueprint.system_prompt)
