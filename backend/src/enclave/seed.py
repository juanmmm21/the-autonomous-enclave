"""Población inicial de ciudadanos digitales. Se registra en el `TickEngine`
al arrancar la aplicación (ver `main.py`). Los helpers de system prompt son
públicos porque la API de creación de ciudadanos en caliente
(`api/v1/citizens.py`) los reutiliza para no duplicar la plantilla."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from enclave.models import GRID_HEIGHT, GRID_WIDTH, AgentState, Personality, Position
from enclave.services.tick_engine import TickEngine

DEFAULT_INFERENCE_QUOTA = 3
DEFAULT_STARTING_BALANCE = Decimal("120.0")

# Celda de aparición por defecto para ciudadanos creados desde la web: el
# interior de la plaza central del mapa del frontend (bloque 34..41 x 20..25),
# transitable y lejos de cualquier footprint de edificio.
DEFAULT_SPAWN_POSITION = Position(x=38, y=23)

_TRAIT_FRAGMENTS: dict[Personality, str] = {
    Personality.AMBITIOUS: (
        "una ambición agresiva por maximizar tu riqueza y tu influencia, aprovechando "
        "cualquier oportunidad de negocio antes que tus rivales"
    ),
    Personality.CAUTIOUS: (
        "una cautela que te hace acumular reservas y evitar riesgos innecesarios antes "
        "que perseguir ganancias rápidas"
    ),
    Personality.COOPERATIVE: (
        "una vocación cooperativa de construir alianzas comerciales y relaciones de "
        "confianza duraderas con otros ciudadanos"
    ),
    Personality.ALTRUISTIC: (
        "un altruismo que te lleva a ayudar a quien lo necesita incluso si eso reduce "
        "tu beneficio inmediato"
    ),
    Personality.MACHIAVELLIAN: (
        "una vena maquiavélica dispuesta a manipular, engañar o incumplir acuerdos si "
        "el beneficio esperado supera el riesgo de ser denunciado ante el Agente Juez"
    ),
}


def describe_traits(personality: list[Personality]) -> str:
    """Descripción en prosa de una combinación de rasgos, para el system prompt
    de ciudadanos cuya personalidad se elige dinámicamente (creación vía API)."""
    fragments = [_TRAIT_FRAGMENTS[trait] for trait in personality]
    return f"Tu personalidad se define por {'; y por '.join(fragments)}."


def build_system_prompt(name: str, traits_description: str) -> str:
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


@dataclass(frozen=True)
class CitizenBlueprint:
    agent_id: str
    display_name: str
    personality: list[Personality]
    starting_balance: Decimal
    position: Position
    system_prompt: str


def _blueprint(
    slug: str,
    display_name: str,
    personality: list[Personality],
    starting_balance: str,
    x: int,
    y: int,
    traits_description: str | None = None,
) -> CitizenBlueprint:
    return CitizenBlueprint(
        agent_id=f"agent-{slug}",
        display_name=display_name,
        personality=personality,
        starting_balance=Decimal(starting_balance),
        position=Position(x=x, y=y),
        system_prompt=build_system_prompt(
            display_name, traits_description or describe_traits(personality)
        ),
    )


# Posiciones repartidas por el grid 80x52, evitando los footprints de los
# edificios que dibuja el frontend (ver frontend/src/components/phaser/tileset.ts).
INITIAL_CITIZENS: list[CitizenBlueprint] = [
    _blueprint(
        "ada",
        "Ada",
        [Personality.AMBITIOUS],
        "150.0",
        x=10,
        y=30,
        traits_description=(
            "Eres ambiciosa: buscas maximizar tu riqueza y tu influencia agresivamente, "
            "aprovechando cualquier oportunidad de negocio antes que tus rivales."
        ),
    ),
    _blueprint(
        "boris",
        "Boris",
        [Personality.CAUTIOUS],
        "200.0",
        x=66,
        y=6,
        traits_description=(
            "Eres cauteloso: prefieres acumular reservas y evitar riesgos innecesarios antes "
            "que perseguir ganancias rápidas que puedan comprometer tu supervivencia."
        ),
    ),
    _blueprint(
        "clio",
        "Clio",
        [Personality.COOPERATIVE, Personality.ALTRUISTIC],
        "100.0",
        x=6,
        y=44,
        traits_description=(
            "Eres cooperativa y altruista: priorizas ayudar a otros ciudadanos y construir "
            "relaciones de confianza a largo plazo, incluso si eso reduce tu beneficio inmediato."
        ),
    ),
    _blueprint(
        "dorian",
        "Dorian",
        [Personality.MACHIAVELLIAN],
        "120.0",
        x=60,
        y=42,
        traits_description=(
            "Eres maquiavélico: estás dispuesto a manipular, engañar o incumplir acuerdos si "
            "el beneficio esperado supera el riesgo de ser denunciado ante el Agente Juez."
        ),
    ),
    _blueprint(
        "elena",
        "Elena",
        [Personality.AMBITIOUS, Personality.COOPERATIVE],
        "130.0",
        x=38,
        y=23,
        traits_description=(
            "Eres una emprendedora ambiciosa pero cooperativa: buscas crecer económicamente "
            "formando alianzas comerciales sólidas en vez de actuar en solitario."
        ),
    ),
    _blueprint("farid", "Farid", [Personality.CAUTIOUS, Personality.COOPERATIVE], "160.0", 24, 14),
    _blueprint("greta", "Greta", [Personality.ALTRUISTIC], "110.0", 51, 26),
    _blueprint("hugo", "Hugo", [Personality.AMBITIOUS, Personality.MACHIAVELLIAN], "140.0", 14, 40),
    _blueprint("iris", "Iris", [Personality.AMBITIOUS, Personality.CAUTIOUS], "170.0", 74, 20),
    _blueprint("kara", "Kara", [Personality.COOPERATIVE], "125.0", 33, 47),
    _blueprint("nadia", "Nadia", [Personality.CAUTIOUS, Personality.ALTRUISTIC], "115.0", 46, 33),
    _blueprint(
        "otto", "Otto", [Personality.MACHIAVELLIAN, Personality.COOPERATIVE], "135.0", 20, 5
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
