import Phaser from "phaser";
import { useEffect, useRef } from "react";

import type { AgentState } from "../../types/api";
import { GRID_HEIGHT, GRID_WIDTH, MainScene, TILE_SIZE } from "./MainScene";

interface GameCanvasProps {
  agents: AgentState[];
  onSelectAgent: (agentId: string) => void;
}

/** Envuelve el juego Phaser en un componente React y reenvía cada snapshot de
 * agentes a la escena activa sin recrear el `Phaser.Game` en cada render. */
export function GameCanvas({ agents, onSelectAgent }: GameCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const gameRef = useRef<Phaser.Game | null>(null);

  useEffect(() => {
    if (!containerRef.current || gameRef.current) {
      return;
    }

    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: containerRef.current,
      width: GRID_WIDTH * TILE_SIZE,
      height: GRID_HEIGHT * TILE_SIZE,
      backgroundColor: "#0b0f1a",
      scene: [MainScene],
    });
    gameRef.current = game;

    game.events.once("ready", () => {
      const scene = game.scene.getScene("MainScene") as MainScene;
      scene.onAgentSelected = onSelectAgent;
    });

    return () => {
      gameRef.current?.destroy(true);
      gameRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- el juego se crea una única vez
  }, []);

  useEffect(() => {
    const scene = gameRef.current?.scene.getScene("MainScene") as MainScene | undefined;
    scene?.syncAgents(agents);
  }, [agents]);

  return <div ref={containerRef} className="overflow-hidden rounded-lg border border-slate-800" />;
}
