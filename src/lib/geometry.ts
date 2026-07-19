export interface Point {
  x: number;
  y: number;
}

export const TILE_WIDTH = 60;
export const TILE_HEIGHT = 30;

export const isoToScreen = (gridX: number, gridY: number, origin: Point): Point => ({
  x: origin.x + (gridX - gridY) * (TILE_WIDTH / 2),
  y: origin.y + (gridX + gridY) * (TILE_HEIGHT / 2),
});
