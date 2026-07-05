import Phaser from "phaser";

import type { AgentState } from "../../types/api";
import { GRID_HEIGHT, GRID_WIDTH, TILE_SIZE } from "./mapConstants";
import {
  ANIMATED_SCENERY,
  CITIZEN_SHEET_KEYS,
  IMAGE_ASSETS,
  PLAZA_EMBLEM,
  SCENERY,
  SHEET_ASSETS,
  TILESET_BASE,
  citizenSheetFor,
  groundTextureAt,
} from "./tileset";

export { GRID_HEIGHT, GRID_WIDTH, TILE_SIZE };

const STATUS_COLOR: Record<AgentState["status"], number> = {
  alive: 0x5eead4,
  sleeping: 0x818cf8,
  bankrupt: 0xf59e0b,
  terminated: 0x334155,
};

/**
 * El backend solo emite una posición nueva cada tick (~5s, marcado por la
 * inferencia del LLM), así que el tween de paseo cubre casi todo el intervalo
 * para que el ciudadano camine de forma continua en vez de teletransportarse
 * y quedarse congelado esperando el siguiente tick.
 */
const MOVE_DURATION_MS = 4200;

/** Distancia de los pies al centro del contenedor (ancla la base del sprite). */
const FOOT_OFFSET = 14;

interface AgentView {
  container: Phaser.GameObjects.Container;
  sprite: Phaser.GameObjects.Sprite;
  sheetKey: string;
  gridX: number;
  gridY: number;
  moveTween: Phaser.Tweens.Tween | null;
}

/**
 * Mapa pixel-art de la ciudad: baldosas, edificios y atrezzo generados en
 * build-time (`scripts/generate_tileset.py`) y un sprite animado por
 * ciudadano, sincronizado con los snapshots que llegan por WebSocket.
 */
export class MainScene extends Phaser.Scene {
  private views = new Map<string, AgentView>();
  private sceneReady = false;
  private pendingAgents: AgentState[] | null = null;

  /** Asignado desde `GameCanvas` para propagar clics sobre un ciudadano a React. */
  onAgentSelected: ((agentId: string) => void) | null = null;

  constructor() {
    super("MainScene");
  }

  preload(): void {
    for (const asset of IMAGE_ASSETS) {
      this.load.image(asset.key, `${TILESET_BASE}/${asset.file}`);
    }
    for (const asset of SHEET_ASSETS) {
      this.load.spritesheet(asset.key, `${TILESET_BASE}/${asset.file}`, {
        frameWidth: asset.frameWidth,
        frameHeight: asset.frameHeight,
      });
    }
  }

  create(): void {
    this.registerAnimations();

    // Suelo: la variante de cada celda es determinista (hash por celda).
    for (let x = 0; x < GRID_WIDTH; x += 1) {
      for (let y = 0; y < GRID_HEIGHT; y += 1) {
        this.add
          .image(x * TILE_SIZE, y * TILE_SIZE, groundTextureAt(x, y))
          .setOrigin(0, 0)
          .setDepth(0);
      }
    }

    this.add.image(PLAZA_EMBLEM.x, PLAZA_EMBLEM.y, PLAZA_EMBLEM.key).setDepth(1);

    // Edificios y atrezzo, puramente decorativos (sin colisión ni lógica):
    // anclados por la base y ordenados por profundidad = línea de suelo, para
    // que los ciudadanos pasen por delante o por detrás según su Y.
    for (const item of SCENERY) {
      this.add.image(item.x, item.y, item.key).setOrigin(0.5, 1).setDepth(item.y);
    }
    for (const item of ANIMATED_SCENERY) {
      this.add
        .sprite(item.x, item.y, item.key)
        .setOrigin(0.5, 1)
        .setDepth(item.y)
        .play(item.anim);
    }

    this.sceneReady = true;
    if (this.pendingAgents) {
      const pending = this.pendingAgents;
      this.pendingAgents = null;
      this.syncAgents(pending);
    }
  }

  update(): void {
    // Orden de dibujo por línea de pies, recalculado mientras se mueven.
    for (const view of this.views.values()) {
      view.container.setDepth(view.container.y + FOOT_OFFSET);
    }
  }

  /** Sincroniza los sprites de agentes con el último snapshot recibido por WebSocket. */
  syncAgents(agents: AgentState[]): void {
    if (!this.sceneReady) {
      // Un snapshot puede llegar antes de que los assets terminen de cargar.
      this.pendingAgents = agents;
      return;
    }

    const seenIds = new Set<string>();

    for (const agent of agents) {
      seenIds.add(agent.agent_id);
      const centerX = agent.position.x * TILE_SIZE + TILE_SIZE / 2;
      const centerY = agent.position.y * TILE_SIZE + TILE_SIZE / 2;

      let view = this.views.get(agent.agent_id);
      if (!view) {
        view = this.createAgentView(agent, centerX, centerY);
        this.views.set(agent.agent_id, view);
      } else if (view.gridX !== agent.position.x || view.gridY !== agent.position.y) {
        this.startWalk(view, agent, centerX, centerY);
      }

      view.sprite.setTint(STATUS_COLOR[agent.status]);
    }

    for (const [agentId, view] of this.views) {
      if (!seenIds.has(agentId)) {
        view.moveTween?.remove();
        this.tweens.killTweensOf([view.container, view.sprite]);
        view.container.destroy();
        this.views.delete(agentId);
      }
    }
  }

  private registerAnimations(): void {
    for (const key of CITIZEN_SHEET_KEYS) {
      this.anims.create({
        key: `${key}-idle`,
        frames: this.anims.generateFrameNumbers(key, { frames: [0, 1] }),
        frameRate: 1.6,
        repeat: -1,
      });
      this.anims.create({
        key: `${key}-walk`,
        frames: this.anims.generateFrameNumbers(key, { frames: [2, 3, 4, 5] }),
        frameRate: 7,
        repeat: -1,
      });
    }
    this.anims.create({
      key: "obelisk-pulse",
      frames: this.anims.generateFrameNumbers("prop-obelisk", { frames: [0, 1, 2, 3] }),
      frameRate: 3,
      yoyo: true,
      repeat: -1,
    });
    this.anims.create({
      key: "server-blink",
      frames: this.anims.generateFrameNumbers("prop-server", { frames: [0, 1] }),
      frameRate: 1.5,
      repeat: -1,
    });
  }

  private createAgentView(agent: AgentState, centerX: number, centerY: number): AgentView {
    const sheetKey = citizenSheetFor(agent.agent_id);

    const shadow = this.add.image(0, FOOT_OFFSET, "prop-shadow");
    const sprite = this.add.sprite(0, FOOT_OFFSET, sheetKey).setOrigin(0.5, 1);
    sprite.play(`${sheetKey}-idle`);
    sprite.setInteractive({ useHandCursor: true });
    sprite.on("pointerdown", () => this.onAgentSelected?.(agent.agent_id));

    const label = this.add
      .text(0, FOOT_OFFSET - 44, agent.display_name, {
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: "10px",
        color: "#dce5f0",
      })
      .setOrigin(0.5, 1)
      .setStroke("#0a0e14", 3)
      .setResolution(2);

    const container = this.add.container(centerX, centerY, [shadow, sprite, label]);
    container.setDepth(centerY + FOOT_OFFSET);

    // Balanceo de reposo perpetuo: aunque el agente no reciba una posición
    // nueva en varios ticks, nunca parece una estatua congelada.
    this.tweens.add({
      targets: sprite,
      y: FOOT_OFFSET - 1.5,
      duration: 1100,
      delay: (this.views.size % 5) * 180,
      yoyo: true,
      repeat: -1,
      ease: Phaser.Math.Easing.Sine.InOut,
    });

    return {
      container,
      sprite,
      sheetKey,
      gridX: agent.position.x,
      gridY: agent.position.y,
      moveTween: null,
    };
  }

  private startWalk(
    view: AgentView,
    agent: AgentState,
    centerX: number,
    centerY: number,
  ): void {
    const deltaX = agent.position.x - view.gridX;
    view.gridX = agent.position.x;
    view.gridY = agent.position.y;

    if (deltaX !== 0) {
      view.sprite.setFlipX(deltaX < 0);
    }

    view.moveTween?.remove();
    view.sprite.play(`${view.sheetKey}-walk`, true);
    view.moveTween = this.tweens.add({
      targets: view.container,
      x: centerX,
      y: centerY,
      duration: MOVE_DURATION_MS,
      ease: Phaser.Math.Easing.Linear,
      onComplete: () => {
        view.moveTween = null;
        view.sprite.play(`${view.sheetKey}-idle`, true);
      },
    });
  }
}
