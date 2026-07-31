const TERMINAL_ROWS = Object.freeze(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]);

export function parseBreadboardAddress(address) {
  const normalized = String(address ?? "").trim().toUpperCase();
  const terminal = /^([A-J])([1-9]|[12][0-9]|30)$/.exec(normalized);
  if (terminal) {
    const row = terminal[1];
    const column = Number(terminal[2]);
    return {
      address: `${row}${column}`,
      column,
      electricalGroup: `${TERMINAL_ROWS.indexOf(row) < 5 ? "ABCDE" : "FGHIJ"}:${column}`,
      kind: "terminal",
      row,
    };
  }
  const rail = /^(T|B)([+-])([1-9]|[12][0-9]|30)$/.exec(normalized);
  if (!rail) return null;
  return {
    address: normalized,
    column: Number(rail[3]),
    electricalGroup: `${rail[1]}${rail[2]}:${rail[3]}`,
    kind: "rail",
    rail: `${rail[1]}${rail[2]}`,
  };
}

export function breadboardHoleRatios(address) {
  const parsed = parseBreadboardAddress(address);
  if (!parsed) return null;
  const x = 0.0875 + ((parsed.column - 1) / 29) * 0.825;
  if (parsed.kind === "terminal") {
    const rowRatios = [0.28, 0.322, 0.364, 0.406, 0.448, 0.574, 0.616, 0.658, 0.7, 0.742];
    return { x, z: rowRatios[TERMINAL_ROWS.indexOf(parsed.row)] };
  }
  return { x, z: { "T+": 0.116, "T-": 0.16, "B+": 0.866, "B-": 0.91 }[parsed.rail] };
}

function occupiedBreadboardHoles(plan) {
  const occupied = new Set();
  for (const placement of plan?.placements ?? []) {
    Object.values(placement.addresses ?? {}).forEach((address) => {
      if (parseBreadboardAddress(address)) occupied.add(address.toUpperCase());
    });
  }
  return occupied;
}

function candidatesInGroup(parsed) {
  if (parsed.kind === "terminal") {
    const rows = parsed.electricalGroup.startsWith("ABCDE")
      ? TERMINAL_ROWS.slice(0, 5)
      : TERMINAL_ROWS.slice(5);
    return rows.map((row) => `${row}${parsed.column}`);
  }
  return [parsed.address];
}

export function nearestEmptyHole(address, occupied, reserved = new Set()) {
  const parsed = parseBreadboardAddress(address);
  if (!parsed) return null;
  const candidates = candidatesInGroup(parsed);
  const preferredIndex = Math.max(0, candidates.indexOf(parsed.address));
  const ordered = [...candidates].sort((left, right) => (
    Math.abs(candidates.indexOf(left) - preferredIndex)
    - Math.abs(candidates.indexOf(right) - preferredIndex)
  ));
  return ordered.find((candidate) => !occupied.has(candidate) && !reserved.has(candidate)) ?? null;
}

export function resolveBreadboardWires(circuit) {
  const plan = circuit?.assemblyPlan;
  if (!plan?.connections?.length) return circuit?.connections ?? [];
  const breadboard = plan.components?.find((component) => component.assetSlug?.startsWith("breadboard-"));
  if (!breadboard) return circuit?.connections ?? [];

  const originalById = new Map((circuit.connections ?? []).map((connection) => [connection.id, connection]));
  const occupied = occupiedBreadboardHoles(plan);
  const reserved = new Set();

  return plan.connections.flatMap((connection) => {
    const sourceAddress = parseBreadboardAddress(connection.source?.address);
    const targetAddress = parseBreadboardAddress(connection.target?.address);
    if (sourceAddress && targetAddress && sourceAddress.electricalGroup === targetAddress.electricalGroup) {
      return [];
    }

    const original = originalById.get(connection.id) ?? {};
    const mapEndpoint = (endpoint, parsed) => {
      if (!parsed) return { component: endpoint.componentId, pin: endpoint.pin };
      const hole = nearestEmptyHole(endpoint.address, occupied, reserved);
      if (!hole) return null;
      reserved.add(hole);
      return { component: breadboard.instanceId, pin: hole };
    };
    const source = mapEndpoint(connection.source, sourceAddress);
    const target = mapEndpoint(connection.target, targetAddress);
    if (!source || !target) return [];
    return [{
      ...original,
      id: connection.id,
      source: source.component,
      sourcePin: source.pin,
      sourceConnector: sourceAddress ? undefined : original.sourceConnector,
      target: target.component,
      targetPin: target.pin,
      targetConnector: targetAddress ? undefined : original.targetConnector,
      wireType: undefined,
      color: connection.color ?? original.color,
      electricalNode: connection.electricalNode,
    }];
  });
}
