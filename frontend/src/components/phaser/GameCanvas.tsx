import Phaser from "phaser";
import { useEffect, useRef } from "react";

import type { AgentState } from "../../types/api";
import { MainScene } from "./MainScene";

interface GameCanvasProps {
  agents: AgentState[];
  onSelectAgent: (agentId: string) => void;
  /** Ciudadano que la cámara debe seguir suavemente, o `null` para paneo libre (Cambio 4b). */
  followAgentId: string | null;
  /** Se dispara cuando el seguimiento se cancela desde la escena (arrastre manual o el agente desaparece). */
  onFollowCancelled: () => void;
  /** Tick actual y duración del día simulado, para el tinte día/noche; `null` hasta el primer evento. */
  simTime: { tick: number; ticksPerDay: number } | null;
}

const MIN_CANVAS_SIZE_PX = 320;

/** Envuelve el juego Phaser en un componente React y reenvía cada snapshot de
 * agentes a la escena activa sin recrear el `Phaser.Game` en cada render. El
 * canvas se redimensiona con el contenedor (mapa panorámico, Cambio 1) en vez
 * de usar un tamaño fijo en píxeles. */
export function GameCanvas({
  agents,
  onSelectAgent,
  followAgentId,
  onFollowCancelled,
  simTime,
}: GameCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const gameRef = useRef<Phaser.Game | null>(null);

  useEffect(() => {
    if (!containerRef.current || gameRef.current) {
      return;
    }
    const container = containerRef.current;

    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: container,
      backgroundColor: "#0a0e14",
      pixelArt: true, // nearest-neighbor: mantiene nítido el tileset pixel-art
      scale: {
        mode: Phaser.Scale.RESIZE,
        parent: container,
        width: Math.max(container.clientWidth, MIN_CANVAS_SIZE_PX),
        height: Math.max(container.clientHeight, MIN_CANVAS_SIZE_PX),
      },
      scene: [MainScene],
    });
    gameRef.current = game;

    game.events.once("ready", () => {
      const scene = game.scene.getScene("MainScene") as MainScene;
      scene.onAgentSelected = onSelectAgent;
      scene.onFollowCancelled = onFollowCancelled;
    });

    // `Phaser.Scale.RESIZE` ya reacciona a cambios de tamaño de ventana, pero
    // no a cambios del contenedor causados por el propio layout de React
    // (p.ej. colapsar el panel lateral): un ResizeObserver cubre ese caso.
    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        game.scale.resize(width, height);
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      gameRef.current?.destroy(true);
      gameRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- el juego se crea una única vez
  }, []);

  useEffect(() => {
    const scene = gameRef.current?.scene.getScene("MainScene") as MainScene | undefined;
    scene?.syncAgents(agents);
  }, [agents]);

  useEffect(() => {
    const scene = gameRef.current?.scene.getScene("MainScene") as MainScene | undefined;
    scene?.setFollowedAgent(followAgentId);
  }, [followAgentId]);

  useEffect(() => {
    if (!simTime) return;
    const scene = gameRef.current?.scene.getScene("MainScene") as MainScene | undefined;
    scene?.setSimTime(simTime.tick, simTime.ticksPerDay);
  }, [simTime]);

  return <div ref={containerRef} className="h-full w-full" />;
}
