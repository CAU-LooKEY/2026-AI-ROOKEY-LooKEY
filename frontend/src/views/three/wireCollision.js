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

export function endpointEgressPoint(point, obstacle, padding = 0.22) {
  if (!obstacle) return { ...point };
  const insideX = point.x >= obstacle.minX && point.x <= obstacle.maxX;
  const insideZ = point.z >= obstacle.minZ && point.z <= obstacle.maxZ;
  if (!insideX || !insideZ) return { ...point };

  const exits = [
    { axis: "x", distance: Math.abs(point.x - obstacle.minX), value: obstacle.minX - padding },
    { axis: "x", distance: Math.abs(obstacle.maxX - point.x), value: obstacle.maxX + padding },
    { axis: "z", distance: Math.abs(point.z - obstacle.minZ), value: obstacle.minZ - padding },
    { axis: "z", distance: Math.abs(obstacle.maxZ - point.z), value: obstacle.maxZ + padding },
  ].sort((left, right) => left.distance - right.distance);

  return {
    ...point,
    [exits[0].axis]: exits[0].value,
  };
}
