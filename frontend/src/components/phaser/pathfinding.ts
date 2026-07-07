import { GRID_HEIGHT, GRID_WIDTH } from "./mapConstants";

/**
 * Pathfinder de rejilla puro (sin dependencias de Phaser): recibe una celda de
 * origen, una de destino y un predicado de transitabilidad, y devuelve la
 * ruta más corta como una lista de waypoints en coordenadas de celda. Usado
 * por `MainScene` tanto para el desplazamiento dirigido por el backend como
 * para el deambular local (Cambios 2 y 3).
 */

export interface Cell {
  x: number;
  y: number;
}

export type IsWalkable = (x: number, y: number) => boolean;

interface SearchNode {
  cell: Cell;
  g: number;
  f: number;
  parent: SearchNode | null;
}

/** 8 direcciones (incluye diagonales) para que el paseo se vea natural, no solo en cruz. */
const DIRECTIONS: readonly Cell[] = [
  { x: 1, y: 0 },
  { x: -1, y: 0 },
  { x: 0, y: 1 },
  { x: 0, y: -1 },
  { x: 1, y: 1 },
  { x: 1, y: -1 },
  { x: -1, y: 1 },
  { x: -1, y: -1 },
];

function cellKey(x: number, y: number): string {
  return `${x},${y}`;
}

/** Distancia octil: heurística admisible para movimiento en 8 direcciones con coste diagonal sqrt(2). */
function octileDistance(a: Cell, b: Cell): number {
  const dx = Math.abs(a.x - b.x);
  const dy = Math.abs(a.y - b.y);
  const diagonal = Math.min(dx, dy);
  const straight = Math.max(dx, dy) - diagonal;
  return diagonal * Math.SQRT2 + straight;
}

function reconstructPath(node: SearchNode): Cell[] {
  const path: Cell[] = [];
  let current: SearchNode | null = node;
  while (current && current.parent) {
    path.unshift(current.cell);
    current = current.parent;
  }
  return path;
}

function isInBounds(x: number, y: number): boolean {
  return x >= 0 && x < GRID_WIDTH && y >= 0 && y < GRID_HEIGHT;
}

/**
 * A* en rejilla con movimiento de 8 direcciones. Devuelve los waypoints desde
 * (excluyendo) el origen hasta (incluyendo) el destino, o `null` si no existe
 * ruta transitable. Un origen y destino iguales devuelven `[]`.
 */
export function findPath(start: Cell, goal: Cell, isWalkable: IsWalkable): Cell[] | null {
  if (start.x === goal.x && start.y === goal.y) {
    return [];
  }
  if (!isInBounds(goal.x, goal.y) || !isWalkable(goal.x, goal.y)) {
    return null;
  }

  const startNode: SearchNode = {
    cell: start,
    g: 0,
    f: octileDistance(start, goal),
    parent: null,
  };
  const open = new Map<string, SearchNode>([[cellKey(start.x, start.y), startNode]]);
  const closed = new Set<string>();

  while (open.size > 0) {
    let current: SearchNode | null = null;
    let currentKey = "";
    for (const [key, node] of open) {
      if (!current || node.f < current.f) {
        current = node;
        currentKey = key;
      }
    }
    if (!current) {
      break;
    }

    if (current.cell.x === goal.x && current.cell.y === goal.y) {
      return reconstructPath(current);
    }

    open.delete(currentKey);
    closed.add(currentKey);

    for (const direction of DIRECTIONS) {
      const neighborX = current.cell.x + direction.x;
      const neighborY = current.cell.y + direction.y;
      const neighborKey = cellKey(neighborX, neighborY);

      if (closed.has(neighborKey)) continue;
      if (!isInBounds(neighborX, neighborY)) continue;
      if (!isWalkable(neighborX, neighborY)) continue;

      const isDiagonal = direction.x !== 0 && direction.y !== 0;
      if (isDiagonal) {
        // Ambos vecinos ortogonales deben ser transitables: evita "cortar" la
        // esquina de un edificio moviéndose en diagonal entre dos celdas bloqueadas.
        const orthogonalXWalkable = isWalkable(current.cell.x + direction.x, current.cell.y);
        const orthogonalYWalkable = isWalkable(current.cell.x, current.cell.y + direction.y);
        if (!orthogonalXWalkable || !orthogonalYWalkable) continue;
      }

      const stepCost = isDiagonal ? Math.SQRT2 : 1;
      const tentativeG = current.g + stepCost;
      const existing = open.get(neighborKey);
      if (existing && tentativeG >= existing.g) continue;

      open.set(neighborKey, {
        cell: { x: neighborX, y: neighborY },
        g: tentativeG,
        f: tentativeG + octileDistance({ x: neighborX, y: neighborY }, goal),
        parent: current,
      });
    }
  }

  return null;
}
