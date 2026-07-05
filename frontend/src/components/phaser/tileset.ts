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
  let hash = 0;
  for (const char of slug) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return CITIZEN_SHEET_KEYS[hash % CITIZEN_SHEET_KEYS.length];
}

// ---------------------------------------------------------------------------
// Layout del suelo: plaza adoquinada central, caminos de tierra que conectan
// los edificios y hierba con variantes en el resto del grid.
// ---------------------------------------------------------------------------

const PLAZA = { x0: 7, y0: 5, x1: 12, y1: 9 };

function isPlaza(x: number, y: number): boolean {
  return x >= PLAZA.x0 && x <= PLAZA.x1 && y >= PLAZA.y0 && y <= PLAZA.y1;
}

function isPath(x: number, y: number): boolean {
  if (y === 7) return true; // avenida este-oeste
  if (x === 10) return true; // avenida norte-sur
  if (x === 3 && y >= 3 && y <= 6) return true; // acceso al mercado
  if (x === 16 && y >= 3 && y <= 6) return true; // acceso al tribunal
  if (y === 13 && x >= 11 && x <= 16) return true; // camino al banco
  if (x === 16 && y === 12) return true; // umbral del banco
  return false;
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

export const SCENERY: readonly Placement[] = [
  // edificios (2x2 celdas, la puerta mira al sur hacia su camino de acceso)
  { key: "building-market", x: 3 * TILE_SIZE, y: 3 * TILE_SIZE },
  { key: "building-hall", x: 16 * TILE_SIZE, y: 3 * TILE_SIZE },
  { key: "building-bank", x: 16 * TILE_SIZE, y: 12 * TILE_SIZE },
  // arboleda
  { key: "prop-tree-a", ...tileAnchor(0, 2) },
  { key: "prop-tree-b", ...tileAnchor(5, 4) },
  { key: "prop-tree-a", ...tileAnchor(14, 4) },
  { key: "prop-tree-b", ...tileAnchor(18, 5) },
  { key: "prop-tree-a", ...tileAnchor(1, 11) },
  { key: "prop-tree-b", ...tileAnchor(6, 12) },
  { key: "prop-tree-a", ...tileAnchor(18, 9) },
  // farolas: esquinas de la plaza + accesos
  { key: "prop-lamp", ...tileAnchor(7, 5) },
  { key: "prop-lamp", ...tileAnchor(12, 5) },
  { key: "prop-lamp", ...tileAnchor(7, 9) },
  { key: "prop-lamp", ...tileAnchor(12, 9) },
  { key: "prop-lamp", ...tileAnchor(2, 6) },
  { key: "prop-lamp", ...tileAnchor(17, 8) },
  // atrezzo urbano y tecnológico
  { key: "prop-crates", ...tileAnchor(4, 2) },
  { key: "prop-crates", ...tileAnchor(17, 11) },
  { key: "prop-solar", ...tileAnchor(13, 10) },
  { key: "prop-solar", ...tileAnchor(14, 10) },
  { key: "prop-antenna", ...tileAnchor(19, 2) },
];

export const ANIMATED_SCENERY: readonly AnimatedPlacement[] = [
  // obelisco holográfico en el centro de la plaza
  { key: "prop-obelisk", x: 10 * TILE_SIZE, y: 7.875 * TILE_SIZE, anim: "obelisk-pulse" },
  // rack de servidores junto al tribunal
  { key: "prop-server", ...tileAnchor(18, 2), anim: "server-blink" },
];

/** Emblema de circuito bajo el obelisco, centrado en la plaza. */
export const PLAZA_EMBLEM: Placement = {
  key: "plaza-emblem",
  x: 10 * TILE_SIZE,
  y: 7.5 * TILE_SIZE,
};
