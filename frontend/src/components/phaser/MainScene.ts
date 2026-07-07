import Phaser from "phaser";

import type { AgentState } from "../../types/api";
import { GRID_HEIGHT, GRID_WIDTH, TILE_SIZE } from "./mapConstants";
import { type Cell, findPath } from "./pathfinding";
import {
  ANIMATED_SCENERY,
  BUILDINGS,
  CITIZEN_SHEET_KEYS,
  IMAGE_ASSETS,
  PLAZA_EMBLEM,
  SCENERY,
  SHEET_ASSETS,
  TILESET_BASE,
  citizenAccentColorFor,
  citizenSheetFor,
  citizenWalkSpeedFor,
  citizenWanderSeedFor,
  footprintAnchor,
  groundTextureAt,
  isBuildingBlocked,
} from "./tileset";

export { GRID_HEIGHT, GRID_WIDTH, TILE_SIZE };

const STATUS_COLOR: Record<AgentState["status"], number> = {
  alive: 0x5eead4,
  sleeping: 0x818cf8,
  bankrupt: 0xf59e0b,
  terminated: 0x334155,
};

/** Distancia de los pies al centro del contenedor (ancla la base del sprite). */
const FOOT_OFFSET = 14;

/** Deambular local (Cambio 3): radio de búsqueda de celda libre y pausa entre tramos. */
const WANDER_MIN_RADIUS = 1;
const WANDER_MAX_RADIUS = 3;
const WANDER_PAUSE_MIN_MS = 1000;
const WANDER_PAUSE_MAX_MS = 3000;
/** El deambular es un paseo relajado sin rumbo, más lento que un desplazamiento dirigido. */
const WANDER_SPEED_FACTOR = 0.75;

/** Cámara: paneo con arrastre, zoom con rueda (clamped) y paneo opcional con teclado.
 * El zoom mínimo NO es una constante: se calcula dinámicamente contra el tamaño
 * real del viewport (ver `computeMinZoom`) para que nunca se vea fondo negro
 * fuera del mundo al alejar. */
const ZOOM_MAX = 2.2;
const CAMERA_INITIAL_ZOOM = 0.85;
const DRAG_THRESHOLD_PX = 4;
const KEYBOARD_PAN_SPEED_PX_PER_S = 320;
/** Suavizado del seguimiento de cámara (Cambio 4b): 0 = instantáneo, 1 = nunca alcanza. */
const FOLLOW_LERP = 0.08;

/** Globo de diálogo flotante con el último `last_reasoning` recibido (Cambio 4b). */
const REASONING_BUBBLE_MS = 6000;
const REASONING_BUBBLE_MAX_CHARS = 90;
/** Compensa la altura variable de los edificios sin necesitar un mapa de alturas exacto. */
const BUILDING_LABEL_OFFSET_PX = 72;

/** Minimapa fijo en la esquina inferior izquierda: toda la ciudad en miniatura. */
const MINIMAP_WIDTH_PX = 176;
const MINIMAP_MARGIN_PX = 12;
const MINIMAP_DEPTH = 100_000;
const MINIMAP_COLORS = {
  grass: 0x1c3423,
  path: 0x4a3c29,
  plaza: 0x38425a,
  building: 0x76849c,
  viewport: 0xdce5f0,
} as const;

/** Tinte día/noche ligado a `tick % ticks_per_day` (el ciclo de sueño del backend). */
const NIGHT_TINT_COLOR = 0x0a1030;
const NIGHT_MAX_ALPHA = 0.3;
/** La noche cae en el último tramo del día simulado; el ciclo de sueño corre justo en el límite. */
const NIGHT_RAMP_START_PHASE = 0.55;
const NIGHT_RAMP_END_PHASE = 0.9;
const NIGHT_FADE_MS = 900;
const NIGHT_DEPTH = 50_000;

/** Popups de balance: el coste pasivo rutinario (~1 SC/tick) se filtra para que
 * el mapa no se llene de "-1.0" perpetuos; solo eventos económicos reales
 * (compras, transferencias, multas, subvenciones) generan popup. */
const BALANCE_POPUP_MIN_ABS_DELTA = 1.5;
const BALANCE_POPUP_RISE_PX = 26;
const BALANCE_POPUP_MS = 1400;

type MovementMode = "idle" | "directed" | "wander" | "wander-pause";

interface AgentView {
  container: Phaser.GameObjects.Container;
  sprite: Phaser.GameObjects.Sprite;
  ring: Phaser.GameObjects.Arc;
  ringTween: Phaser.Tweens.Tween | null;
  ringVisible: boolean;
  bubble: Phaser.GameObjects.Container | null;
  bubbleTimer: Phaser.Time.TimerEvent | null;
  sheetKey: string;
  /** Última posición autoritativa recibida del backend (para detectar un tick nuevo). */
  serverCellX: number;
  serverCellY: number;
  /** Celda donde se encuentra visualmente el sprite ahora mismo (origen del próximo tramo). */
  currentCellX: number;
  currentCellY: number;
  movementMode: MovementMode;
  wanderTimer: Phaser.Time.TimerEvent | null;
  walkSpeedPxPerSec: number;
  wanderRandom: () => number;
  lastReasoning: string | null;
  lastStatus: AgentState["status"];
  /** Balance del snapshot anterior, para el popup flotante de diferencia (+N/-N SC). */
  lastBalance: string | null;
  accentColor: number;
}

interface MinimapView {
  container: Phaser.GameObjects.Container;
  dynamicLayer: Phaser.GameObjects.Graphics;
  clickZone: Phaser.GameObjects.Zone;
  widthPx: number;
  heightPx: number;
  /** Píxeles de minimapa por píxel de mundo. */
  worldScale: number;
}

/** Generador pseudoaleatorio determinista (mulberry32): reproducible entre recargas, sin depender de Math.random(). */
function createSeededRandom(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Mapa pixel-art de la ciudad: baldosas, edificios y atrezzo generados en
 * build-time (`scripts/generate_tileset.py`) y un sprite animado por
 * ciudadano, sincronizado con los snapshots que llegan por WebSocket.
 *
 * El desplazamiento de cada ciudadano sigue rutas reales calculadas por
 * `pathfinding.ts` (esquivando los footprints de los edificios) y, cuando
 * no hay una posición nueva del backend que perseguir, deambula localmente en
 * bucle para no quedarse congelado entre ticks. Un minimapa fijo en la esquina
 * inferior izquierda resume toda la ciudad y permite saltar la cámara con un
 * clic, y un tinte día/noche sigue el ciclo de sueño del backend.
 */
export class MainScene extends Phaser.Scene {
  private views = new Map<string, AgentView>();
  private sceneReady = false;
  private pendingAgents: AgentState[] | null = null;
  private pendingSimTime: { tick: number; ticksPerDay: number } | null = null;

  private followedAgentId: string | null = null;
  private isDragging = false;
  private pointerDownAt: { x: number; y: number } | null = null;
  private keyboardKeys: Record<string, Phaser.Input.Keyboard.Key> | null = null;

  private minimap: MinimapView | null = null;
  private nightOverlay: Phaser.GameObjects.Rectangle | null = null;
  private nightTween: Phaser.Tweens.Tween | null = null;
  /**
   * Cámara dedicada a la UI fija (minimapa, tinte nocturno): la cámara
   * principal hace zoom y scroll, y en Phaser eso escala también a los objetos
   * con scrollFactor 0, así que la única forma de mantener la UI clavada en
   * pantalla es renderizarla con una segunda cámara sin zoom ni scroll.
   */
  private uiCamera: Phaser.Cameras.Scene2D.Camera | null = null;

  /** Asignado desde `GameCanvas` para propagar clics sobre un ciudadano a React. */
  onAgentSelected: ((agentId: string) => void) | null = null;
  /** Asignado desde `GameCanvas`: notifica a React cuando el seguimiento de cámara se cancela por sí solo. */
  onFollowCancelled: (() => void) | null = null;

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

    // Edificios y atrezzo, puramente decorativos (la colisión real la define
    // `isBuildingBlocked` sobre los mismos footprints, no estos sprites),
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

    // Etiquetas persistentes sobre los edificios (Cambio 4), igual que ya
    // existen sobre los ciudadanos, para no depender solo del modal de ayuda.
    for (const building of BUILDINGS) {
      const anchor = footprintAnchor(building.footprint);
      this.add
        .text(anchor.x, anchor.y - BUILDING_LABEL_OFFSET_PX, building.displayName, {
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: "11px",
          color: "#dce5f0",
        })
        .setOrigin(0.5, 1)
        .setStroke("#0a0e14", 3)
        .setResolution(2)
        .setDepth(anchor.y + 1);
    }

    const worldWidthPx = GRID_WIDTH * TILE_SIZE;
    const worldHeightPx = GRID_HEIGHT * TILE_SIZE;
    this.cameras.main.setBounds(0, 0, worldWidthPx, worldHeightPx);
    this.cameras.main.setZoom(Math.max(CAMERA_INITIAL_ZOOM, this.computeMinZoom()));
    this.cameras.main.centerOn(PLAZA_EMBLEM.x, PLAZA_EMBLEM.y);
    this.setupCameraControls();

    this.nightOverlay = this.add
      .rectangle(0, 0, this.cameras.main.width, this.cameras.main.height, NIGHT_TINT_COLOR)
      .setOrigin(0, 0)
      .setAlpha(0)
      .setDepth(NIGHT_DEPTH);

    this.createMinimap();
    this.setupUiCamera();

    this.scale.on(Phaser.Scale.Events.RESIZE, this.handleViewportResize, this);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.scale.off(Phaser.Scale.Events.RESIZE, this.handleViewportResize, this);
    });

    this.sceneReady = true;
    if (this.pendingAgents) {
      const pending = this.pendingAgents;
      this.pendingAgents = null;
      this.syncAgents(pending);
    }
    if (this.pendingSimTime) {
      const pending = this.pendingSimTime;
      this.pendingSimTime = null;
      this.setSimTime(pending.tick, pending.ticksPerDay);
    }
  }

  update(_time: number, delta: number): void {
    // Orden de dibujo por línea de pies, recalculado mientras se mueven.
    for (const view of this.views.values()) {
      view.container.setDepth(view.container.y + FOOT_OFFSET);
    }
    this.updateKeyboardPan(delta);
    this.redrawMinimapDynamicLayer();
  }

  /** Predicado de transitabilidad: dentro del grid y fuera de todo footprint de edificio. */
  private isWalkable = (x: number, y: number): boolean => {
    return x >= 0 && x < GRID_WIDTH && y >= 0 && y < GRID_HEIGHT && !isBuildingBlocked(x, y);
  };

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

      let view = this.views.get(agent.agent_id);
      if (!view) {
        view = this.createAgentView(agent);
        this.views.set(agent.agent_id, view);
        if (agent.agent_id === this.followedAgentId) {
          this.cameras.main.startFollow(view.container, true, FOLLOW_LERP, FOLLOW_LERP);
        }
      } else if (view.serverCellX !== agent.position.x || view.serverCellY !== agent.position.y) {
        view.serverCellX = agent.position.x;
        view.serverCellY = agent.position.y;
        this.startDirectedWalk(view, { x: agent.position.x, y: agent.position.y });
      }

      this.applyStatusBehavior(view, agent.status);

      if (agent.last_reasoning && agent.last_reasoning !== view.lastReasoning) {
        this.showReasoningBubble(view, agent.last_reasoning);
      }
      view.lastReasoning = agent.last_reasoning;

      if (view.lastBalance !== null && view.lastBalance !== agent.balance) {
        this.showBalancePopup(view, Number(agent.balance) - Number(view.lastBalance));
      }
      view.lastBalance = agent.balance;

      view.sprite.setTint(STATUS_COLOR[agent.status]);
    }

    for (const [agentId, view] of this.views) {
      if (!seenIds.has(agentId)) {
        this.destroyView(agentId, view);
      }
    }
  }

  /**
   * Tinte día/noche: `tick % ticksPerDay` marca la fase del día simulado; la
   * noche cae en su último tramo (el ciclo de sueño del backend corre justo en
   * el límite de día) y amanece al empezar el siguiente.
   */
  setSimTime(tick: number, ticksPerDay: number): void {
    if (!this.sceneReady || !this.nightOverlay) {
      this.pendingSimTime = { tick, ticksPerDay };
      return;
    }
    const phase = (tick % ticksPerDay) / ticksPerDay;
    const ramp = Phaser.Math.Clamp(
      (phase - NIGHT_RAMP_START_PHASE) / (NIGHT_RAMP_END_PHASE - NIGHT_RAMP_START_PHASE),
      0,
      1,
    );
    const targetAlpha = NIGHT_MAX_ALPHA * ramp * ramp * (3 - 2 * ramp); // smoothstep

    this.nightTween?.remove();
    this.nightTween = this.tweens.add({
      targets: this.nightOverlay,
      alpha: targetAlpha,
      duration: NIGHT_FADE_MS,
      ease: Phaser.Math.Easing.Sine.InOut,
    });
  }

  /** Activa/desactiva el seguimiento de cámara sobre un ciudadano (Cambio 4b). */
  setFollowedAgent(agentId: string | null): void {
    this.followedAgentId = agentId;
    if (!agentId) {
      this.cameras.main.stopFollow();
      return;
    }
    const view = this.views.get(agentId);
    if (view) {
      this.cameras.main.startFollow(view.container, true, FOLLOW_LERP, FOLLOW_LERP);
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

  /**
   * Cota inferior de zoom para que el mundo cubra el viewport en ambas
   * dimensiones: por debajo de este valor aparecería fondo negro fuera del
   * mapa (`setBounds` solo acota el scroll, no el zoom). Se recalcula en cada
   * uso porque con `Phaser.Scale.RESIZE` el tamaño real de la cámara cambia
   * con el contenedor.
   */
  private computeMinZoom(): number {
    const camera = this.cameras.main;
    const worldWidthPx = GRID_WIDTH * TILE_SIZE;
    const worldHeightPx = GRID_HEIGHT * TILE_SIZE;
    const coveringZoom = Math.max(camera.width / worldWidthPx, camera.height / worldHeightPx);
    // En un viewport absurdamente grande el zoom de cobertura podría superar
    // ZOOM_MAX; en ese caso cubrir el viewport gana sobre el techo de zoom.
    return Math.min(coveringZoom, ZOOM_MAX);
  }

  /**
   * Reparte los objetos entre las dos cámaras: el mundo solo se renderiza en
   * la principal y la UI fija solo en `uiCamera`. Los objetos de mundo creados
   * DESPUÉS (vistas de agentes, popups) se excluyen en su punto de creación.
   */
  private setupUiCamera(): void {
    const uiObjects: Phaser.GameObjects.GameObject[] = [];
    if (this.nightOverlay) uiObjects.push(this.nightOverlay);
    if (this.minimap) uiObjects.push(this.minimap.container, this.minimap.clickZone);

    const uiCamera = this.cameras.add(0, 0, this.scale.width, this.scale.height);
    uiCamera.ignore(this.children.list.filter((obj) => !uiObjects.includes(obj)));
    this.cameras.main.ignore(uiObjects);
    this.uiCamera = uiCamera;
  }

  private handleViewportResize(): void {
    const camera = this.cameras.main;
    this.uiCamera?.setSize(this.scale.width, this.scale.height);
    if (this.nightOverlay) {
      this.nightOverlay.setSize(this.scale.width, this.scale.height);
    }
    this.layoutMinimap();

    const minZoom = this.computeMinZoom();
    if (camera.zoom < minZoom) {
      camera.setZoom(minZoom);
    }
  }

  private setupCameraControls(): void {
    const camera = this.cameras.main;

    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      // Un gesto iniciado sobre el minimapa es un salto de cámara, no un paneo.
      if (this.isPointerOverMinimap(pointer)) return;
      this.pointerDownAt = { x: pointer.x, y: pointer.y };
      this.isDragging = false;
    });

    this.input.on("pointermove", (pointer: Phaser.Input.Pointer) => {
      if (!pointer.isDown || !this.pointerDownAt) return;

      if (!this.isDragging) {
        const totalDx = pointer.x - this.pointerDownAt.x;
        const totalDy = pointer.y - this.pointerDownAt.y;
        if (Math.hypot(totalDx, totalDy) < DRAG_THRESHOLD_PX) return;
        this.isDragging = true;
        // El arrastre manual siempre gana sobre el seguimiento automático (Cambio 4b).
        if (this.followedAgentId) {
          this.followedAgentId = null;
          camera.stopFollow();
          this.onFollowCancelled?.();
        }
      }

      camera.scrollX -= (pointer.x - pointer.prevPosition.x) / camera.zoom;
      camera.scrollY -= (pointer.y - pointer.prevPosition.y) / camera.zoom;
    });

    this.input.on("pointerup", () => {
      this.pointerDownAt = null;
      this.isDragging = false;
    });

    this.input.on(
      "wheel",
      (
        pointer: Phaser.Input.Pointer,
        _objects: Phaser.GameObjects.GameObject[],
        _dx: number,
        dy: number,
      ) => {
        const worldBefore = camera.getWorldPoint(pointer.x, pointer.y);
        const zoomStep = dy > 0 ? -0.1 : 0.1;
        camera.zoom = Phaser.Math.Clamp(camera.zoom + zoomStep, this.computeMinZoom(), ZOOM_MAX);
        const worldAfter = camera.getWorldPoint(pointer.x, pointer.y);
        camera.scrollX += worldBefore.x - worldAfter.x;
        camera.scrollY += worldBefore.y - worldAfter.y;
      },
    );

    this.keyboardKeys =
      (this.input.keyboard?.addKeys("W,A,S,D,UP,DOWN,LEFT,RIGHT") as Record<
        string,
        Phaser.Input.Keyboard.Key
      >) ?? null;
  }

  private updateKeyboardPan(delta: number): void {
    if (!this.keyboardKeys || this.followedAgentId) return;

    const camera = this.cameras.main;
    const step = (KEYBOARD_PAN_SPEED_PX_PER_S * delta) / 1000 / camera.zoom;
    if (this.keyboardKeys.A?.isDown || this.keyboardKeys.LEFT?.isDown) camera.scrollX -= step;
    if (this.keyboardKeys.D?.isDown || this.keyboardKeys.RIGHT?.isDown) camera.scrollX += step;
    if (this.keyboardKeys.W?.isDown || this.keyboardKeys.UP?.isDown) camera.scrollY -= step;
    if (this.keyboardKeys.S?.isDown || this.keyboardKeys.DOWN?.isDown) camera.scrollY += step;
  }

  // -------------------------------------------------------------------------
  // Minimapa: toda la ciudad en miniatura, con el rectángulo del viewport y un
  // punto de color de acento por ciudadano; clic para saltar la cámara allí.
  // -------------------------------------------------------------------------

  private createMinimap(): void {
    const widthPx = MINIMAP_WIDTH_PX;
    const cellPx = widthPx / GRID_WIDTH;
    const heightPx = GRID_HEIGHT * cellPx;
    const worldScale = cellPx / TILE_SIZE;

    // Capa estática (se dibuja una sola vez): suelo simplificado + edificios.
    const staticLayer = this.add.graphics();
    staticLayer.fillStyle(MINIMAP_COLORS.grass, 1);
    staticLayer.fillRect(0, 0, widthPx, heightPx);
    for (let x = 0; x < GRID_WIDTH; x += 1) {
      for (let y = 0; y < GRID_HEIGHT; y += 1) {
        const texture = groundTextureAt(x, y);
        if (texture.startsWith("tile-plaza")) {
          staticLayer.fillStyle(MINIMAP_COLORS.plaza, 1);
        } else if (texture.startsWith("tile-path")) {
          staticLayer.fillStyle(MINIMAP_COLORS.path, 1);
        } else {
          continue;
        }
        staticLayer.fillRect(x * cellPx, y * cellPx, Math.ceil(cellPx), Math.ceil(cellPx));
      }
    }
    staticLayer.fillStyle(MINIMAP_COLORS.building, 1);
    for (const building of BUILDINGS) {
      const { x0, y0, x1, y1 } = building.footprint;
      staticLayer.fillRect(
        x0 * cellPx,
        y0 * cellPx,
        (x1 - x0 + 1) * cellPx,
        (y1 - y0 + 1) * cellPx,
      );
    }
    staticLayer.lineStyle(1, 0x2dd4bf, 0.55);
    staticLayer.strokeRect(0, 0, widthPx, heightPx);

    const backdrop = this.add
      .rectangle(-2, -2, widthPx + 4, heightPx + 4, 0x0a0e14, 0.85)
      .setOrigin(0, 0);

    const dynamicLayer = this.add.graphics();
    const container = this.add
      .container(0, 0, [backdrop, staticLayer, dynamicLayer])
      .setDepth(MINIMAP_DEPTH);

    const clickZone = this.add
      .zone(0, 0, widthPx, heightPx)
      .setOrigin(0, 0)
      .setDepth(MINIMAP_DEPTH + 1)
      .setInteractive({ useHandCursor: true });
    clickZone.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      this.jumpCameraViaMinimap(pointer);
    });

    this.minimap = { container, dynamicLayer, clickZone, widthPx, heightPx, worldScale };
    this.layoutMinimap();
  }

  /** Ancla el minimapa a la esquina inferior izquierda del viewport actual. */
  private layoutMinimap(): void {
    if (!this.minimap) return;
    const x = MINIMAP_MARGIN_PX;
    const y = this.scale.height - this.minimap.heightPx - MINIMAP_MARGIN_PX;
    this.minimap.container.setPosition(x, y);
    this.minimap.clickZone.setPosition(x, y);
  }

  private isPointerOverMinimap(pointer: Phaser.Input.Pointer): boolean {
    if (!this.minimap) return false;
    const { container, widthPx, heightPx } = this.minimap;
    return (
      pointer.x >= container.x &&
      pointer.x <= container.x + widthPx &&
      pointer.y >= container.y &&
      pointer.y <= container.y + heightPx
    );
  }

  private jumpCameraViaMinimap(pointer: Phaser.Input.Pointer): void {
    if (!this.minimap) return;
    // Saltar la cámara manualmente gana sobre el seguimiento automático,
    // igual que el arrastre.
    if (this.followedAgentId) {
      this.followedAgentId = null;
      this.cameras.main.stopFollow();
      this.onFollowCancelled?.();
    }
    const worldX = (pointer.x - this.minimap.container.x) / this.minimap.worldScale;
    const worldY = (pointer.y - this.minimap.container.y) / this.minimap.worldScale;
    this.cameras.main.centerOn(worldX, worldY);
  }

  /** Capa dinámica del minimapa, redibujada cada frame: viewport + ciudadanos. */
  private redrawMinimapDynamicLayer(): void {
    if (!this.minimap) return;
    const { dynamicLayer, worldScale, widthPx, heightPx } = this.minimap;
    const camera = this.cameras.main;

    dynamicLayer.clear();

    for (const view of this.views.values()) {
      const alpha = view.lastStatus === "terminated" ? 0.35 : 1;
      dynamicLayer.fillStyle(view.accentColor, alpha);
      dynamicLayer.fillCircle(
        view.container.x * worldScale,
        view.container.y * worldScale,
        2,
      );
    }

    const viewRect = camera.worldView;
    dynamicLayer.lineStyle(1, MINIMAP_COLORS.viewport, 0.9);
    dynamicLayer.strokeRect(
      Phaser.Math.Clamp(viewRect.x * worldScale, 0, widthPx),
      Phaser.Math.Clamp(viewRect.y * worldScale, 0, heightPx),
      Math.min(viewRect.width * worldScale, widthPx),
      Math.min(viewRect.height * worldScale, heightPx),
    );
  }

  private createAgentView(agent: AgentState): AgentView {
    const sheetKey = citizenSheetFor(agent.agent_id);
    const centerX = agent.position.x * TILE_SIZE + TILE_SIZE / 2;
    const centerY = agent.position.y * TILE_SIZE + TILE_SIZE / 2;

    const ring = this.add
      .circle(0, FOOT_OFFSET + 2, 15, 0x000000, 0)
      .setStrokeStyle(2, STATUS_COLOR.bankrupt, 0.85)
      .setVisible(false);
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

    // Punto de acento determinista junto al nombre: distingue a ciudadanos que
    // comparten hoja de sprites sin pisar el tinte de `status` del sprite.
    const accentColor = citizenAccentColorFor(agent.agent_id);
    const accentDot = this.add.circle(
      -(label.width / 2) - 5,
      FOOT_OFFSET - 49,
      2,
      accentColor,
    );

    const container = this.add.container(centerX, centerY, [
      ring,
      shadow,
      sprite,
      label,
      accentDot,
    ]);
    container.setDepth(centerY + FOOT_OFFSET);
    // Objeto de mundo creado tras el reparto de cámaras: se excluye de la UI.
    this.uiCamera?.ignore(container);

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
      ring,
      ringTween: null,
      ringVisible: false,
      bubble: null,
      bubbleTimer: null,
      sheetKey,
      serverCellX: agent.position.x,
      serverCellY: agent.position.y,
      currentCellX: agent.position.x,
      currentCellY: agent.position.y,
      movementMode: "idle",
      wanderTimer: null,
      walkSpeedPxPerSec: citizenWalkSpeedFor(agent.agent_id),
      wanderRandom: createSeededRandom(citizenWanderSeedFor(agent.agent_id)),
      lastReasoning: null,
      lastStatus: agent.status,
      lastBalance: agent.balance,
      accentColor,
    };
  }

  /**
   * Popup flotante "+N/-N SC" sobre el ciudadano cuando su balance cambia
   * entre dos snapshots. El coste pasivo rutinario queda por debajo del umbral
   * para no llenar el mapa de ruido cada tick.
   */
  private showBalancePopup(view: AgentView, delta: number): void {
    if (!Number.isFinite(delta) || Math.abs(delta) < BALANCE_POPUP_MIN_ABS_DELTA) {
      return;
    }
    const isGain = delta > 0;
    const popup = this.add
      .text(view.container.x, view.container.y - 52, `${isGain ? "+" : ""}${delta.toFixed(1)} SC`, {
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: "10px",
        color: isGain ? "#4ade80" : "#f87171",
      })
      .setOrigin(0.5, 1)
      .setStroke("#0a0e14", 3)
      .setResolution(2)
      .setDepth(view.container.y + FOOT_OFFSET + 1);
    // Objeto de mundo creado tras el reparto de cámaras: se excluye de la UI.
    this.uiCamera?.ignore(popup);

    this.tweens.add({
      targets: popup,
      y: popup.y - BALANCE_POPUP_RISE_PX,
      alpha: 0,
      duration: BALANCE_POPUP_MS,
      ease: Phaser.Math.Easing.Sine.Out,
      onComplete: () => popup.destroy(),
    });
  }

  private destroyView(agentId: string, view: AgentView): void {
    if (agentId === this.followedAgentId) {
      this.followedAgentId = null;
      this.cameras.main.stopFollow();
      this.onFollowCancelled?.();
    }
    this.cancelMovement(view);
    view.ringTween?.remove();
    view.bubble?.destroy();
    if (view.bubbleTimer) this.time.removeEvent(view.bubbleTimer);
    this.tweens.killTweensOf([view.container, view.sprite]);
    view.container.destroy();
    this.views.delete(agentId);
  }

  /** Cancela cualquier movimiento en curso (tramo dirigido o de deambular) y la pausa pendiente. */
  private cancelMovement(view: AgentView): void {
    this.tweens.killTweensOf(view.container);
    if (view.wanderTimer) {
      this.time.removeEvent(view.wanderTimer);
      view.wanderTimer = null;
    }
    view.movementMode = "idle";
  }

  private applyStatusBehavior(view: AgentView, status: AgentState["status"]): void {
    view.lastStatus = status;
    this.updateStatusRing(view, status);

    if (status !== "alive") {
      // Dormido/en bancarrota/terminado: nunca deambula, y si una posición
      // autoritativa llegó a la vez que el cambio de estado, se refleja al
      // instante en vez de dejar el sprite a medio camino de un tween cancelado.
      if (view.movementMode !== "idle") {
        this.cancelMovement(view);
      }
      view.currentCellX = view.serverCellX;
      view.currentCellY = view.serverCellY;
      view.container.setPosition(
        view.serverCellX * TILE_SIZE + TILE_SIZE / 2,
        view.serverCellY * TILE_SIZE + TILE_SIZE / 2,
      );
      view.sprite.play(`${view.sheetKey}-idle`, true);
      view.container.setAlpha(status === "terminated" ? 0.45 : 1);
      return;
    }

    view.container.setAlpha(1);
    if (view.movementMode === "idle") {
      this.scheduleWander(view);
    }
  }

  private updateStatusRing(view: AgentView, status: AgentState["status"]): void {
    const shouldShow = status === "bankrupt" || status === "terminated";
    if (shouldShow === view.ringVisible) return;
    view.ringVisible = shouldShow;

    if (!shouldShow) {
      view.ring.setVisible(false);
      view.ringTween?.remove();
      view.ringTween = null;
      return;
    }

    view.ring.setStrokeStyle(2, STATUS_COLOR[status], 0.85);
    view.ring.setScale(1);
    view.ring.setAlpha(0.85);
    view.ring.setVisible(true);
    view.ringTween?.remove();
    view.ringTween = this.tweens.add({
      targets: view.ring,
      scale: 1.7,
      alpha: 0,
      duration: 1400,
      repeat: -1,
      ease: Phaser.Math.Easing.Sine.Out,
    });
  }

  private showReasoningBubble(view: AgentView, reasoning: string): void {
    view.bubble?.destroy();
    if (view.bubbleTimer) {
      this.time.removeEvent(view.bubbleTimer);
      view.bubbleTimer = null;
    }

    const truncated =
      reasoning.length > REASONING_BUBBLE_MAX_CHARS
        ? `${reasoning.slice(0, REASONING_BUBBLE_MAX_CHARS - 3)}...`
        : reasoning;

    const paddingX = 8;
    const paddingY = 6;
    const text = this.add
      .text(0, -paddingY, truncated, {
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: "9px",
        color: "#0a0e14",
        wordWrap: { width: 150 },
        align: "center",
      })
      .setOrigin(0.5, 1)
      .setResolution(2);

    const bg = this.add
      .rectangle(0, 0, text.width + paddingX * 2, text.height + paddingY * 2, 0xdce5f0, 0.95)
      .setOrigin(0.5, 1)
      .setStrokeStyle(1, 0x2dd4bf, 0.7);

    const bubble = this.add.container(0, FOOT_OFFSET - 56, [bg, text]);
    view.container.add(bubble);
    view.bubble = bubble;

    view.bubbleTimer = this.time.delayedCall(REASONING_BUBBLE_MS, () => {
      view.bubbleTimer = null;
      this.tweens.add({
        targets: bubble,
        alpha: 0,
        duration: 400,
        onComplete: () => {
          bubble.destroy();
          if (view.bubble === bubble) view.bubble = null;
        },
      });
    });
  }

  /** Camina la ruta calculada por el pathfinder desde la celda actual hasta `target`. */
  private startDirectedWalk(view: AgentView, target: Cell): void {
    this.cancelMovement(view);
    view.movementMode = "directed";

    const origin: Cell = { x: view.currentCellX, y: view.currentCellY };
    // Si el backend (que no conoce los edificios del frontend) sitúa al agente
    // sobre una celda bloqueada, no hay ruta transitable posible: se refleja
    // igualmente la posición autoritativa con un tramo directo en vez de
    // dejar al ciudadano "atascado" negándose a moverse.
    const path = findPath(origin, target, this.isWalkable) ?? [target];

    this.followPath(view, path, view.walkSpeedPxPerSec, () => {
      view.movementMode = "idle";
      if (view.lastStatus === "alive") {
        this.scheduleWander(view);
      } else {
        view.sprite.play(`${view.sheetKey}-idle`, true);
      }
    });
  }

  /** Encadena un tween lineal por cada waypoint de la ruta, a velocidad constante. */
  private followPath(
    view: AgentView,
    path: readonly Cell[],
    speedPxPerSec: number,
    onDone: () => void,
  ): void {
    if (path.length === 0) {
      onDone();
      return;
    }

    view.sprite.play(`${view.sheetKey}-walk`, true);

    const playLeg = (index: number): void => {
      if (index >= path.length) {
        view.sprite.play(`${view.sheetKey}-idle`, true);
        onDone();
        return;
      }

      const cell = path[index];
      const previousCellX = index === 0 ? view.currentCellX : path[index - 1].x;
      const deltaX = cell.x - previousCellX;
      if (deltaX !== 0) {
        view.sprite.setFlipX(deltaX < 0);
      }

      const targetX = cell.x * TILE_SIZE + TILE_SIZE / 2;
      const targetY = cell.y * TILE_SIZE + TILE_SIZE / 2;
      const distance = Phaser.Math.Distance.Between(
        view.container.x,
        view.container.y,
        targetX,
        targetY,
      );
      const duration = Math.max(120, (distance / speedPxPerSec) * 1000);

      this.tweens.add({
        targets: view.container,
        x: targetX,
        y: targetY,
        duration,
        ease: Phaser.Math.Easing.Linear,
        onComplete: () => {
          view.currentCellX = cell.x;
          view.currentCellY = cell.y;
          playLeg(index + 1);
        },
      });
    };

    playLeg(0);
  }

  /** Programa la siguiente ronda de deambular tras una pausa de 1-3s. */
  private scheduleWander(view: AgentView): void {
    view.movementMode = "wander-pause";
    const pauseMs =
      WANDER_PAUSE_MIN_MS + view.wanderRandom() * (WANDER_PAUSE_MAX_MS - WANDER_PAUSE_MIN_MS);
    view.wanderTimer = this.time.delayedCall(pauseMs, () => {
      view.wanderTimer = null;
      this.startWanderLeg(view);
    });
  }

  private startWanderLeg(view: AgentView): void {
    const target = this.pickWanderTarget(view);
    if (!target) {
      // No hay celda libre cerca (poco probable, pero la avenida más próxima
      // podría estar rodeada de edificios): reintenta más tarde en vez de
      // quedarse en un bucle síncrono.
      this.scheduleWander(view);
      return;
    }

    view.movementMode = "wander";
    const origin: Cell = { x: view.currentCellX, y: view.currentCellY };
    const path = findPath(origin, target, this.isWalkable) ?? [];
    this.followPath(view, path, view.walkSpeedPxPerSec * WANDER_SPEED_FACTOR, () => {
      view.movementMode = "idle";
      if (view.lastStatus === "alive") {
        this.scheduleWander(view);
      }
    });
  }

  private pickWanderTarget(view: AgentView): Cell | null {
    const candidates: Cell[] = [];
    for (let dx = -WANDER_MAX_RADIUS; dx <= WANDER_MAX_RADIUS; dx += 1) {
      for (let dy = -WANDER_MAX_RADIUS; dy <= WANDER_MAX_RADIUS; dy += 1) {
        const distance = Math.max(Math.abs(dx), Math.abs(dy));
        if (distance < WANDER_MIN_RADIUS || distance > WANDER_MAX_RADIUS) continue;

        const x = view.currentCellX + dx;
        const y = view.currentCellY + dy;
        if (!this.isWalkable(x, y)) continue;
        candidates.push({ x, y });
      }
    }

    if (candidates.length === 0) {
      return null;
    }
    const index = Math.floor(view.wanderRandom() * candidates.length);
    return candidates[index];
  }
}
