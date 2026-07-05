import Phaser from "phaser";

import type { AgentState } from "../../types/api";

export const TILE_SIZE = 32;
export const GRID_WIDTH = 20;
export const GRID_HEIGHT = 15;

const STATUS_COLOR: Record<AgentState["status"], number> = {
  alive: 0x5eead4,
  sleeping: 0x818cf8,
  bankrupt: 0xf59e0b,
  terminated: 0x334155,
};

/**
 * Mapa pixel-art de la ciudad. Renderiza una cuadrícula placeholder (a falta
 * de tileset artístico) y un marcador circular por ciudadano, posicionado
 * según las coordenadas de `AgentState.position` que llegan por telemetría.
 */
export class MainScene extends Phaser.Scene {
  private agentSprites = new Map<string, Phaser.GameObjects.Arc>();
  private agentLabels = new Map<string, Phaser.GameObjects.Text>();

  /** Asignado desde `GameCanvas` para propagar clics sobre un ciudadano a React. */
  onAgentSelected: ((agentId: string) => void) | null = null;

  constructor() {
    super("MainScene");
  }

  create(): void {
    const grid = this.add.graphics();
    grid.lineStyle(1, 0x1e293b, 0.6);
    for (let x = 0; x <= GRID_WIDTH; x += 1) {
      grid.lineBetween(x * TILE_SIZE, 0, x * TILE_SIZE, GRID_HEIGHT * TILE_SIZE);
    }
    for (let y = 0; y <= GRID_HEIGHT; y += 1) {
      grid.lineBetween(0, y * TILE_SIZE, GRID_WIDTH * TILE_SIZE, y * TILE_SIZE);
    }
  }

  /** Sincroniza los sprites de agentes con el último snapshot recibido por WebSocket. */
  syncAgents(agents: AgentState[]): void {
    const seenIds = new Set<string>();

    for (const agent of agents) {
      seenIds.add(agent.agent_id);
      const centerX = agent.position.x * TILE_SIZE + TILE_SIZE / 2;
      const centerY = agent.position.y * TILE_SIZE + TILE_SIZE / 2;
      const color = STATUS_COLOR[agent.status];

      let sprite = this.agentSprites.get(agent.agent_id);
      if (!sprite) {
        sprite = this.add.circle(centerX, centerY, TILE_SIZE / 3, color);
        sprite.setInteractive({ useHandCursor: true });
        sprite.on("pointerdown", () => this.onAgentSelected?.(agent.agent_id));
        this.agentSprites.set(agent.agent_id, sprite);
      } else {
        sprite.setFillStyle(color);
        this.tweens.add({ targets: sprite, x: centerX, y: centerY, duration: 400 });
      }

      let label = this.agentLabels.get(agent.agent_id);
      if (!label) {
        label = this.add
          .text(centerX, centerY - TILE_SIZE / 2 - 4, agent.display_name, {
            fontSize: "10px",
            color: "#e2e8f0",
          })
          .setOrigin(0.5, 1);
        this.agentLabels.set(agent.agent_id, label);
      } else {
        this.tweens.add({
          targets: label,
          x: centerX,
          y: centerY - TILE_SIZE / 2 - 4,
          duration: 400,
        });
      }
    }

    for (const [agentId, sprite] of this.agentSprites) {
      if (!seenIds.has(agentId)) {
        sprite.destroy();
        this.agentSprites.delete(agentId);
        this.agentLabels.get(agentId)?.destroy();
        this.agentLabels.delete(agentId);
      }
    }
  }
}
