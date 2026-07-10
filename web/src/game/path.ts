import type { Point } from './projection'

/**
 * Position along a polyline at fraction `t` of its total arc length. `t` is
 * clamped to [0, 1]. A one-point path returns that point.
 */
export function pointAlongPath(points: Point[], t: number): Point {
  if (points.length === 0) throw new Error('pointAlongPath: empty path')
  if (points.length === 1) return points[0]

  const clamped = Math.max(0, Math.min(1, t))

  const segLengths: number[] = []
  let total = 0
  for (let i = 1; i < points.length; i++) {
    const len = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
    segLengths.push(len)
    total += len
  }
  if (total === 0) return points[0]

  let target = clamped * total
  for (let i = 0; i < segLengths.length; i++) {
    const len = segLengths[i]
    if (target <= len) {
      const f = len === 0 ? 0 : target / len
      return {
        x: points[i].x + (points[i + 1].x - points[i].x) * f,
        y: points[i].y + (points[i + 1].y - points[i].y) * f,
      }
    }
    target -= len
  }
  return points[points.length - 1]
}
