function axisInterval(start, delta, minimum, maximum) {
  if (Math.abs(delta) < 1e-9) {
    return start >= minimum && start <= maximum ? [0, 1] : null;
  }
  const first = (minimum - start) / delta;
  const second = (maximum - start) / delta;
  return [Math.min(first, second), Math.max(first, second)];
}

export function segmentCrossesObstacle(source, target, obstacle, padding = 0.18) {
  const xInterval = axisInterval(
    source.x,
    target.x - source.x,
    obstacle.minX - padding,
    obstacle.maxX + padding,
  );
  const zInterval = axisInterval(
    source.z,
    target.z - source.z,
    obstacle.minZ - padding,
    obstacle.maxZ + padding,
  );
  if (!xInterval || !zInterval) return false;
  const entry = Math.max(0, xInterval[0], zInterval[0]);
  const exit = Math.min(1, xInterval[1], zInterval[1]);
  return entry <= exit;
}

export function obstacleClearanceHeight(
  source,
  target,
  obstacles,
  excludedIds = new Set(),
  clearance = 0.3,
) {
  let height = null;
  for (const obstacle of obstacles) {
    if (excludedIds.has(obstacle.id)) continue;
    if (!segmentCrossesObstacle(source, target, obstacle)) continue;
    height = Math.max(height ?? Number.NEGATIVE_INFINITY, obstacle.maxY + clearance);
  }
  return height;
}
