import Phaser from "phaser";

import { TILE_SIZE } from "./mapConstants";

export const CITIZEN_TEXTURE = "tileset-citizen";
export const GROUND_TILE_TEXTURE = "tileset-ground";
export const MARKET_TEXTURE = "tileset-market";
export const BANK_TEXTURE = "tileset-bank";

/**
 * Genera un pequeño tileset pixel-art directamente por código (sin depender de
 * assets externos): una baldosa de suelo, un sprite de ciudadano recoloreable
 * vía `setTint`, y dos edificios decorativos (mercado y banco) que dan
 * ambientación a la plaza sin estar ligados a lógica de juego.
 */
export function generateTileset(scene: Phaser.Scene): void {
  generateGroundTile(scene);
  generateCitizenSprite(scene);
  generateMarketBuilding(scene);
  generateBankBuilding(scene);
}

function generateGroundTile(scene: Phaser.Scene): void {
  if (scene.textures.exists(GROUND_TILE_TEXTURE)) return;

  const graphics = scene.add.graphics();
  const base = 0x1a2234;
  const light = 0x232d42;
  const speck = 0x2b3654;

  graphics.fillStyle(base, 1);
  graphics.fillRect(0, 0, TILE_SIZE, TILE_SIZE);

  // Losetas 8x8 alternadas para dar textura de adoquinado pixel-art.
  const cell = TILE_SIZE / 4;
  for (let row = 0; row < 4; row += 1) {
    for (let col = 0; col < 4; col += 1) {
      if ((row + col) % 2 === 0) {
        graphics.fillStyle(light, 1);
        graphics.fillRect(col * cell, row * cell, cell, cell);
      }
    }
  }

  // Motas sutiles para romper la repetición del patrón.
  graphics.fillStyle(speck, 1);
  graphics.fillRect(3, 3, 2, 2);
  graphics.fillRect(TILE_SIZE - 6, TILE_SIZE - 6, 2, 2);
  graphics.fillRect(TILE_SIZE - 9, 5, 2, 2);

  graphics.generateTexture(GROUND_TILE_TEXTURE, TILE_SIZE, TILE_SIZE);
  graphics.destroy();
}

function generateCitizenSprite(scene: Phaser.Scene): void {
  if (scene.textures.exists(CITIZEN_TEXTURE)) return;

  const width = 14;
  const height = 20;
  const graphics = scene.add.graphics();

  // Dibujado en blanco puro: cada agente lo retiñe con `setTint(color)` según
  // su estado, sin necesidad de generar una textura por color.
  const white = 0xffffff;

  graphics.fillStyle(0x000000, 0.25);
  graphics.fillEllipse(width / 2, height - 2, 10, 4); // sombra

  graphics.fillStyle(white, 1);
  graphics.fillRect(4, 8, 6, 9); // torso
  graphics.fillRect(2, 9, 2, 6); // brazo izquierdo
  graphics.fillRect(10, 9, 2, 6); // brazo derecho
  graphics.fillRect(4, 15, 2, 4); // pierna izquierda
  graphics.fillRect(8, 15, 2, 4); // pierna derecha
  graphics.fillCircle(width / 2, 4, 4); // cabeza

  graphics.generateTexture(CITIZEN_TEXTURE, width, height);
  graphics.destroy();
}

function generateMarketBuilding(scene: Phaser.Scene): void {
  if (scene.textures.exists(MARKET_TEXTURE)) return;

  const size = TILE_SIZE * 1.5;
  const graphics = scene.add.graphics();

  graphics.fillStyle(0x1c1408, 1);
  graphics.fillRect(4, size * 0.4, size - 8, size * 0.55); // caseta

  graphics.fillStyle(0xb45309, 1); // toldo
  graphics.fillTriangle(0, size * 0.45, size / 2, size * 0.1, size, size * 0.45);
  graphics.fillStyle(0xf59e0b, 1);
  for (let stripe = 0; stripe < 4; stripe += 1) {
    const stripeWidth = size / 4;
    if (stripe % 2 === 0) {
      graphics.fillTriangle(
        stripe * stripeWidth,
        size * 0.45,
        stripe * stripeWidth + stripeWidth,
        size * 0.45,
        size / 2,
        size * 0.1,
      );
    }
  }

  graphics.fillStyle(0x78350f, 1);
  graphics.fillRect(size * 0.4, size * 0.65, size * 0.2, size * 0.3); // puerta

  graphics.generateTexture(MARKET_TEXTURE, size, size);
  graphics.destroy();
}

function generateBankBuilding(scene: Phaser.Scene): void {
  if (scene.textures.exists(BANK_TEXTURE)) return;

  const size = TILE_SIZE * 1.5;
  const graphics = scene.add.graphics();

  graphics.fillStyle(0x1e293b, 1);
  graphics.fillRect(2, size * 0.3, size - 4, size * 0.65); // fachada

  graphics.fillStyle(0x334155, 1);
  graphics.fillRect(0, size * 0.22, size, size * 0.12); // friso del techo

  graphics.fillStyle(0xcbd5e1, 1);
  const columnWidth = size * 0.12;
  const columnGap = size * 0.18;
  for (let column = 0; column < 4; column += 1) {
    graphics.fillRect(
      size * 0.1 + column * columnGap,
      size * 0.34,
      columnWidth,
      size * 0.5,
    );
  }

  graphics.fillStyle(0x0f172a, 1);
  graphics.fillRect(size * 0.42, size * 0.68, size * 0.16, size * 0.27); // puerta

  graphics.generateTexture(BANK_TEXTURE, size, size);
  graphics.destroy();
}
