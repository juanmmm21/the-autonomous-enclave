import Phaser from "phaser";

import type { AgentState } from "../../types/api";
import { GRID_HEIGHT, GRID_WIDTH, TILE_SIZE } from "./mapConstants";
import {
  BANK_TEXTURE,
  CITIZEN_TEXTURE,
  GROUND_TILE_TEXTURE,
  MARKET_TEXTURE,
  generateTileset,
} from "./tileset";

export { GRID_HEIGHT, GRID_WIDTH, TILE_SIZE };

const STATUS_COLOR: Record<AgentState["status"], number> = {
  alive: 0x5eead4,
  sleeping: 0x818cf8,
  bankrupt: 0xf59e0b,
  terminated: 0x334155,
};

/**
 * Mapa pixel-art de la ciudad: suelo generado por código, un mercado y un
 * banco decorativos, y un sprite por ciudadano (recoloreado según su estado)
 * posicionado según las coordenadas de `AgentState.position` por telemetría.
 */
export class MainScene extends Phaser.Scene {
  private agentSprites = new Map<string, Phaser.GameObjects.Sprite>();
  private agentLabels = new Map<string, Phaser.GameObjects.Text>();

  /** Asignado desde `GameCanvas` para propagar clics sobre un ciudadano a React. */
  onAgentSelected: ((agentId: string) => void) | null = null;

  constructor() {
    super("MainScene");
  }

  create(): void {
    generateTileset(this);

    for (let x = 0; x < GRID_WIDTH; x += 1) {
      for (let y = 0; y < GRID_HEIGHT; y += 1) {
        this.add
          .image(x * TILE_SIZE, y * TILE_SIZE, GROUND_TILE_TEXTURE)
          .setOrigin(0, 0)
          .setDepth(0);
      }
    }

    const grid = this.add.graphics().setDepth(1);
    grid.lineStyle(1, 0x0b1120, 0.5);
    for (let x = 0; x <= GRID_WIDTH; x += 1) {
      grid.lineBetween(x * TILE_SIZE, 0, x * TILE_SIZE, GRID_HEIGHT * TILE_SIZE);
    }
    for (let y = 0; y <= GRID_HEIGHT; y += 1) {
      grid.lineBetween(0, y * TILE_SIZE, GRID_WIDTH * TILE_SIZE, y * TILE_SIZE);
    }

    // Edificios puramente decorativos: dan ambientación a la plaza pero no
    // están ligados a ninguna lógica de juego (no hay colisión ni "entrar").
    this.add.image(3 * TILE_SIZE, 2 * TILE_SIZE, MARKET_TEXTURE).setOrigin(0, 0).setDepth(2);
    this.add.image(16 * TILE_SIZE, 11 * TILE_SIZE, BANK_TEXTURE).setOrigin(0, 0).setDepth(2);
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
        sprite = this.add.sprite(centerX, centerY, CITIZEN_TEXTURE).setDepth(3);
        sprite.setTint(color);
        sprite.setInteractive({ useHandCursor: true });
        sprite.on("pointerdown", () => this.onAgentSelected?.(agent.agent_id));
        this.agentSprites.set(agent.agent_id, sprite);
      } else {
        sprite.setTint(color);
        this.tweens.add({ targets: sprite, x: centerX, y: centerY, duration: 400 });
      }

      let label = this.agentLabels.get(agent.agent_id);
      if (!label) {
        label = this.add
          .text(centerX, centerY - TILE_SIZE / 2 - 4, agent.display_name, {
            fontSize: "10px",
            color: "#e2e8f0",
          })
          .setOrigin(0.5, 1)
          .setDepth(4);
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
