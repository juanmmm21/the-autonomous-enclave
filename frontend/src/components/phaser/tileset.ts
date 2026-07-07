import { TILE_SIZE } from "./mapConstants";

/**
 * Manifiesto del tileset pixel-art y layout del mapa de Silicon Polis.
 *
 * Los PNG de `frontend/public/tileset/` se generan en build-time con
 * `scripts/generate_tileset.py` (Python + Pillow, herramienta local del repo,
 * no una dependencia del proyecto) y se cargan como assets normales de Phaser
 * en `MainScene.preload()`. Aquí solo viven los datos: qué archivos cargar,
 * qué baldosa corresponde a cada celda del grid y dónde se coloca cada
 * elemento decorativo.
 */

export const TILESET_BASE = "/tileset";

export interface ImageAssetDef {
  key: string;
  file: string;
}

export interface SheetAssetDef extends ImageAssetDef {
  frameWidth: number;
  frameHeight: number;
}

export const IMAGE_ASSETS: readonly ImageAssetDef[] = [
  { key: "tile-grass-a", file: "grass_a.png" },
  { key: "tile-grass-b", file: "grass_b.png" },
  { key: "tile-grass-c", file: "grass_c.png" },
  { key: "tile-grass-d", file: "grass_d.png" },
  { key: "tile-path-a", file: "path_a.png" },
  { key: "tile-path-b", file: "path_b.png" },
  { key: "tile-plaza-a", file: "plaza_a.png" },
  { key: "tile-plaza-b", file: "plaza_b.png" },
  { key: "plaza-emblem", file: "plaza_emblem.png" },
  { key: "prop-tree-a", file: "tree_a.png" },
  { key: "prop-tree-b", file: "tree_b.png" },
  { key: "prop-lamp", file: "lamp.png" },
  { key: "prop-antenna", file: "antenna.png" },
  { key: "prop-solar", file: "solar.png" },
  { key: "prop-crates", file: "crates.png" },
  { key: "prop-shadow", file: "shadow.png" },
  { key: "building-market", file: "market.png" },
  { key: "building-bank", file: "bank.png" },
  { key: "building-hall", file: "hall.png" },
  { key: "building-lab", file: "lab.png" },
  { key: "building-signal", file: "signal_tower.png" },
  { key: "building-workshop", file: "workshop.png" },
  { key: "building-exchange", file: "exchange.png" },
  { key: "building-housing", file: "housing.png" },
];

export const CITIZEN_SHEET_KEYS = [
  "citizen-ada",
  "citizen-boris",
  "citizen-clio",
  "citizen-dorian",
  "citizen-elena",
] as const;

export const SHEET_ASSETS: readonly SheetAssetDef[] = [
  { key: "citizen-ada", file: "citizen_ada.png", frameWidth: 32, frameHeight: 40 },
  { key: "citizen-boris", file: "citizen_boris.png", frameWidth: 32, frameHeight: 40 },
  { key: "citizen-clio", file: "citizen_clio.png", frameWidth: 32, frameHeight: 40 },
  { key: "citizen-dorian", file: "citizen_dorian.png", frameWidth: 32, frameHeight: 40 },
  { key: "citizen-elena", file: "citizen_elena.png", frameWidth: 32, frameHeight: 40 },
  { key: "prop-obelisk", file: "obelisk.png", frameWidth: 32, frameHeight: 48 },
  { key: "prop-server", file: "server_rack.png", frameWidth: 24, frameHeight: 40 },
];

/** Hash multiplicativo determinista compartido por las derivaciones "por id". */
function hashString(value: string): number {
  let hash = 0;
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
}

/**
 * Cada agente sembrado (`agent-ada`, `agent-boris`, ...) tiene su propia hoja
 * de sprites con peinado/silueta distintivos; un agente desconocido recibe una
 * hoja determinista derivada del hash de su id.
 */
export function citizenSheetFor(agentId: string): string {
  const slug = agentId.toLowerCase().replace(/^agent-/, "");
  const direct = CITIZEN_SHEET_KEYS.find((key) => key === `citizen-${slug}`);
  if (direct) {
    return direct;
  }
  return CITIZEN_SHEET_KEYS[hashString(slug) % CITIZEN_SHEET_KEYS.length];
}

const WALK_SPEED_MIN_PX_PER_S = 90;
const WALK_SPEED_MAX_PX_PER_S = 110;

/**
 * Velocidad de paseo determinista por ciudadano: sin esta variación los 5
 * sprites caminarían siempre al mismo ritmo exacto y se leerían como
 * autómatas sincronizados en vez de personas distintas.
 */
export function citizenWalkSpeedFor(agentId: string): number {
  const span = WALK_SPEED_MAX_PX_PER_S - WALK_SPEED_MIN_PX_PER_S;
  return WALK_SPEED_MIN_PX_PER_S + ((hashString(agentId) % 997) / 997) * span;
}

/**
 * Semilla del generador pseudoaleatorio que decide radio/celda/pausa del
 * deambular libre (Cambio 3). Se deriva del id en vez de usar `Math.random()`
 * directamente para que el comportamiento sea reproducible entre recargas.
 */
export function citizenWanderSeedFor(agentId: string): number {
  return hashString(`${agentId}-wander`);
}

/**
 * Acento visual por ciudadano: con muchos más agentes que hojas de sprites
 * base (5), varios comparten silueta; este color determinista se muestra como
 * un punto junto a la etiqueta del nombre (y en el censo del panel lateral)
 * para distinguirlos SIN retintar el sprite, cuyo tinte ya codifica el
 * `status` (vivo/dormido/bancarrota/terminado) y no debe pisarse.
 */
const ACCENT_PALETTE: readonly number[] = [
  0xf472b6, // rosa
  0xfb923c, // naranja
  0xfacc15, // amarillo
  0xa3e635, // lima
  0x34d399, // esmeralda
  0x38bdf8, // celeste
  0xc084fc, // violeta
  0xf87171, // coral
  0xe879f9, // fucsia
  0x94a3b8, // pizarra clara
];

export function citizenAccentColorFor(agentId: string): number {
  return ACCENT_PALETTE[hashString(`${agentId}-accent`) % ACCENT_PALETTE.length];
}

/** El mismo acento, como color CSS para los paneles React (censo de ciudadanos). */
export function citizenAccentCssFor(agentId: string): string {
  return `#${citizenAccentColorFor(agentId).toString(16).padStart(6, "0")}`;
}

// ---------------------------------------------------------------------------
// Layout del suelo: avenidas norte-sur y este-oeste que forman manzanas,
// una plaza central que ocupa una manzana entera y hierba con variantes en
// el resto del grid. Diseñado para el grid 80x52 (ver mapConstants.ts).
// ---------------------------------------------------------------------------

/** Columnas de las avenidas norte-sur (constantes en x, recorren todo el alto). */
const AVENUES_NS: readonly number[] = [6, 15, 24, 33, 42, 51, 60, 69];
/** Filas de las avenidas este-oeste (constantes en y, recorren todo el ancho). */
const AVENUES_EW: readonly number[] = [5, 12, 19, 26, 33, 40, 47];

const AVENUES_NS_SET = new Set(AVENUES_NS);
const AVENUES_EW_SET = new Set(AVENUES_EW);

/** Manzanas (rango de celdas inclusive) entre avenidas consecutivas, más los bordes del mapa. */
const COLUMN_BLOCKS: ReadonlyArray<readonly [number, number]> = [
  [0, 5],
  [7, 14],
  [16, 23],
  [25, 32],
  [34, 41],
  [43, 50],
  [52, 59],
  [61, 68],
  [70, 79],
];
const ROW_BLOCKS: ReadonlyArray<readonly [number, number]> = [
  [0, 4],
  [6, 11],
  [13, 18],
  [20, 25],
  [27, 32],
  [34, 39],
  [41, 46],
  [48, 51],
];

/** La plaza ocupa la manzana central entera (colBlock 4, rowBlock 3): sin avenida que la atraviese. */
const PLAZA = { x0: 34, y0: 20, x1: 41, y1: 25 };
const PLAZA_BLOCK_ID = "4,3";

function isPlaza(x: number, y: number): boolean {
  return x >= PLAZA.x0 && x <= PLAZA.x1 && y >= PLAZA.y0 && y <= PLAZA.y1;
}

export interface CellRect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface BuildingDef {
  key: string;
  displayName: string;
  footprint: CellRect;
  /** Celdas de la calle de acceso (fuera del footprint) que conectan con la avenida más cercana. */
  accessSpur: readonly (readonly [number, number])[];
}

/**
 * Fábrica de edificios anclados a una avenida este-oeste: el footprint 2x2
 * ocupa las dos filas justo encima de `avenueRow` menos la calle de acceso,
 * que conecta la puerta con la avenida. Mantiene coherentes footprint (colisión
 * del pathfinder), anclaje visual y acceso sin autorar 4 coordenadas a mano.
 */
function buildingAboveAvenue(
  key: string,
  displayName: string,
  x0: number,
  avenueRow: number,
): BuildingDef {
  return {
    key,
    displayName,
    footprint: { x0, y0: avenueRow - 3, x1: x0 + 1, y1: avenueRow - 2 },
    accessSpur: [
      [x0, avenueRow - 1],
      [x0 + 1, avenueRow - 1],
    ],
  };
}

/**
 * Los edificios de Silicon Polis, repartidos por las manzanas del grid 80x52.
 * Cada tipo de activo de la economía de silicio (docs/vision.md) tiene sede
 * física: mercado (compraventa general), banco (SimCoin), ayuntamiento (el
 * Juez), laboratorio (vector_pack), torre de señales (alpha_signal), taller
 * (code_script) y bolsa (financial_derivative); las viviendas son relleno
 * residencial no económico. El footprint es la fuente de verdad tanto para el
 * anclaje visual (`SCENERY`, derivado de él) como para la colisión del
 * pathfinder: ambos quedan garantizados coherentes entre sí.
 */
export const BUILDINGS: readonly BuildingDef[] = [
  buildingAboveAvenue("building-market", "Mercado", 9, 12),
  buildingAboveAvenue("building-market", "Mercado", 63, 33),
  buildingAboveAvenue("building-hall", "Ayuntamiento", 37, 12),
  buildingAboveAvenue("building-bank", "Banco", 19, 26),
  buildingAboveAvenue("building-bank", "Banco", 56, 40),
  buildingAboveAvenue("building-lab", "Lab. de Vectores", 27, 19),
  buildingAboveAvenue("building-lab", "Lab. de Vectores", 71, 12),
  buildingAboveAvenue("building-signal", "Torre de Señales", 45, 19),
  buildingAboveAvenue("building-signal", "Torre de Señales", 9, 40),
  buildingAboveAvenue("building-workshop", "Taller de Scripts", 17, 12),
  buildingAboveAvenue("building-workshop", "Taller de Scripts", 49, 33),
  buildingAboveAvenue("building-exchange", "Bolsa de Derivados", 29, 33),
  buildingAboveAvenue("building-exchange", "Bolsa de Derivados", 53, 12),
  buildingAboveAvenue("building-housing", "Viviendas", 2, 19),
  buildingAboveAvenue("building-housing", "Viviendas", 36, 40),
  buildingAboveAvenue("building-housing", "Viviendas", 72, 40),
  buildingAboveAvenue("building-housing", "Viviendas", 2, 47),
];

export const BUILDING_FOOTPRINTS: readonly CellRect[] = BUILDINGS.map(
  (building) => building.footprint,
);

/** Usado por el pathfinder (Cambio 2): toda celda dentro de un footprint de edificio bloquea el paso. */
export function isBuildingBlocked(x: number, y: number): boolean {
  return BUILDING_FOOTPRINTS.some(
    (fp) => x >= fp.x0 && x <= fp.x1 && y >= fp.y0 && y <= fp.y1,
  );
}

const BUILDING_ACCESS_CELLS = new Set(
  BUILDINGS.flatMap((building) => building.accessSpur.map(([x, y]) => `${x},${y}`)),
);

function isPath(x: number, y: number): boolean {
  if (AVENUES_NS_SET.has(x)) return true;
  if (AVENUES_EW_SET.has(y)) return true;
  return BUILDING_ACCESS_CELLS.has(`${x},${y}`);
}

/** Hash determinista por celda para elegir variantes sin aleatoriedad en runtime. */
function cellHash(x: number, y: number): number {
  return (((x + 1) * 73856093) ^ ((y + 1) * 19349663)) >>> 0;
}

export function groundTextureAt(x: number, y: number): string {
  const hash = cellHash(x, y);
  if (isPlaza(x, y)) {
    return hash % 7 === 0 ? "tile-plaza-b" : "tile-plaza-a";
  }
  if (isPath(x, y)) {
    return hash % 5 === 0 ? "tile-path-b" : "tile-path-a";
  }
  const roll = hash % 33;
  if (roll === 0) return "tile-grass-d"; // brote bioluminiscente (raro)
  if (roll <= 3) return "tile-grass-c"; // flores
  if (roll <= 11) return "tile-grass-b"; // matas
  return "tile-grass-a";
}

// ---------------------------------------------------------------------------
// Decoración: edificios y atrezzo, anclados por la base (origin 0.5, 1) para
// poder ordenarlos por profundidad con los ciudadanos.
// ---------------------------------------------------------------------------

export interface Placement {
  key: string;
  x: number;
  y: number;
}

export interface AnimatedPlacement extends Placement {
  anim: string;
}

/** Punto medio-inferior de una celda del grid, en píxeles. */
function tileAnchor(tileX: number, tileY: number): { x: number; y: number } {
  return { x: (tileX + 0.5) * TILE_SIZE, y: (tileY + 1) * TILE_SIZE };
}

/** Punto medio-inferior de un footprint rectangular, en píxeles (ancla la imagen del edificio). */
export function footprintAnchor(footprint: CellRect): { x: number; y: number } {
  return {
    x: ((footprint.x0 + footprint.x1 + 1) / 2) * TILE_SIZE,
    y: (footprint.y1 + 1) * TILE_SIZE,
  };
}

const BUILDING_PLACEMENTS: readonly Placement[] = BUILDINGS.map((building) => ({
  key: building.key,
  ...footprintAnchor(building.footprint),
}));

/** Farolas en las 4 esquinas de la plaza y flanqueando la entrada de cada edificio. */
const LANDMARK_LAMPS: readonly Placement[] = [
  { key: "prop-lamp", ...tileAnchor(PLAZA.x0, PLAZA.y0) },
  { key: "prop-lamp", ...tileAnchor(PLAZA.x1, PLAZA.y0) },
  { key: "prop-lamp", ...tileAnchor(PLAZA.x0, PLAZA.y1) },
  { key: "prop-lamp", ...tileAnchor(PLAZA.x1, PLAZA.y1) },
  ...BUILDINGS.map((building) => ({
    key: "prop-lamp",
    ...tileAnchor(building.footprint.x1 + 1, building.footprint.y1),
  })),
];

const PLAZA_CENTER_CELL_X = (PLAZA.x0 + PLAZA.x1 + 1) / 2;
const PLAZA_CENTER_CELL_Y = (PLAZA.y0 + PLAZA.y1 + 1) / 2;

/** Emblema de circuito bajo el obelisco, centrado en la plaza. */
export const PLAZA_EMBLEM: Placement = {
  key: "plaza-emblem",
  x: PLAZA_CENTER_CELL_X * TILE_SIZE,
  y: PLAZA_CENTER_CELL_Y * TILE_SIZE,
};

const LANDMARK_ANIMATED: readonly AnimatedPlacement[] = [
  // obelisco holográfico en el centro de la plaza (ligeramente adelantado respecto al emblema)
  {
    key: "prop-obelisk",
    x: PLAZA_CENTER_CELL_X * TILE_SIZE,
    y: (PLAZA_CENTER_CELL_Y + 0.375) * TILE_SIZE,
    anim: "obelisk-pulse",
  },
];

function blockIdContaining(x: number, y: number): string | null {
  const colIdx = COLUMN_BLOCKS.findIndex(([start, end]) => x >= start && x <= end);
  const rowIdx = ROW_BLOCKS.findIndex(([start, end]) => y >= start && y <= end);
  if (colIdx < 0 || rowIdx < 0) return null;
  return `${colIdx},${rowIdx}`;
}

/**
 * Manzanas ya ocupadas por la plaza o un edificio: la generación de atrezzo
 * las salta. Se deriva de `BUILDINGS` (cada footprint 2x2 cabe en una única
 * manzana) en vez de mantener una lista manual que quedaría desincronizada
 * al mover o añadir edificios.
 */
function computeReservedBlocks(): Set<string> {
  const reserved = new Set<string>([PLAZA_BLOCK_ID]);
  for (const building of BUILDINGS) {
    const blockId = blockIdContaining(building.footprint.x0, building.footprint.y0);
    if (blockId) reserved.add(blockId);
  }
  return reserved;
}

const RESERVED_BLOCKS = computeReservedBlocks();
/** Manzanas reservadas al "distrito tecnológico": antena y rack de servidores, en vez del atrezzo genérico. */
const ANTENNA_BLOCK = "8,0";
const SERVER_BLOCK = "0,7";

/** Hash de manzana independiente del hash de celda, para no correlacionar ambos patrones. */
function blockHash(colIdx: number, rowIdx: number): number {
  return (((colIdx + 7) * 2654435761) ^ ((rowIdx + 13) * 40503)) >>> 0;
}

function blockCenter(range: readonly [number, number]): number {
  return Math.floor((range[0] + range[1]) / 2);
}

interface GeneratedScenery {
  placements: Placement[];
  animated: AnimatedPlacement[];
}

/**
 * Reparte el atrezzo decorativo ya existente (árboles, farolas, cajas,
 * paneles solares) por las manzanas que no son ni la plaza ni un edificio,
 * para que la ciudad ampliada (Cambio 1) se sienta poblada en vez de vacía,
 * sin autorar a mano decenas de coordenadas: la variedad y posición son
 * deterministas por manzana (mismo criterio que `groundTextureAt`).
 */
function buildBlockScenery(): GeneratedScenery {
  const placements: Placement[] = [];
  const animated: AnimatedPlacement[] = [];

  for (let colIdx = 0; colIdx < COLUMN_BLOCKS.length; colIdx += 1) {
    for (let rowIdx = 0; rowIdx < ROW_BLOCKS.length; rowIdx += 1) {
      const blockId = `${colIdx},${rowIdx}`;
      if (RESERVED_BLOCKS.has(blockId)) continue;

      const colRange = COLUMN_BLOCKS[colIdx];
      const rowRange = ROW_BLOCKS[rowIdx];
      const centerX = blockCenter(colRange);
      const centerY = blockCenter(rowRange);

      if (blockId === ANTENNA_BLOCK) {
        placements.push({ key: "prop-antenna", ...tileAnchor(centerX, centerY) });
        continue;
      }
      if (blockId === SERVER_BLOCK) {
        animated.push({
          key: "prop-server",
          ...tileAnchor(centerX, centerY),
          anim: "server-blink",
        });
        continue;
      }

      const hash = blockHash(colIdx, rowIdx);
      switch (hash % 5) {
        case 0:
          placements.push({
            key: (colIdx + rowIdx) % 2 === 0 ? "prop-tree-a" : "prop-tree-b",
            ...tileAnchor(centerX, centerY),
          });
          break;
        case 1:
          placements.push({ key: "prop-lamp", ...tileAnchor(centerX, centerY) });
          break;
        case 2:
          placements.push({ key: "prop-crates", ...tileAnchor(centerX, centerY) });
          break;
        case 3: {
          const secondX = Math.min(centerX + 1, colRange[1]);
          placements.push({ key: "prop-solar", ...tileAnchor(centerX, centerY) });
          if (secondX !== centerX) {
            placements.push({ key: "prop-solar", ...tileAnchor(secondX, centerY) });
          }
          break;
        }
        default:
          // Manzana deliberadamente vacía (solo hierba): una ciudad real también respira.
          break;
      }
    }
  }

  return { placements, animated };
}

const GENERATED_SCENERY = buildBlockScenery();

export const SCENERY: readonly Placement[] = [
  ...BUILDING_PLACEMENTS,
  ...LANDMARK_LAMPS,
  ...GENERATED_SCENERY.placements,
];

export const ANIMATED_SCENERY: readonly AnimatedPlacement[] = [
  ...LANDMARK_ANIMATED,
  ...GENERATED_SCENERY.animated,
];
