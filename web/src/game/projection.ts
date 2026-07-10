export interface Point {
  x: number
  y: number
}

export interface ProjectionOptions {
  worldWidth: number
  worldHeight: number
  viewWidth: number
  viewHeight: number
  padding: number
}

/**
 * Project a world coordinate (0..worldWidth / 0..worldHeight) into SVG view
 * coordinates, inset by `padding`. The y-axis is flipped so higher world y is
 * higher on screen (SVG y grows downward).
 */
export function projectPoint(
  x: number,
  y: number,
  opts: ProjectionOptions,
): Point {
  const { worldWidth, worldHeight, viewWidth, viewHeight, padding } = opts
  const innerW = viewWidth - 2 * padding
  const innerH = viewHeight - 2 * padding
  return {
    x: padding + (x / worldWidth) * innerW,
    y: padding + ((worldHeight - y) / worldHeight) * innerH,
  }
}
