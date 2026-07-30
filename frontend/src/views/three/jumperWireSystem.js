export const ConnectorGender = Object.freeze({
  MALE: "male",
  FEMALE: "female",
});

export const WireColorRole = Object.freeze({
  POWER: "power",
  GROUND: "ground",
  SIGNAL: "signal",
});

export const JUMPER_SPEC = Object.freeze({
  pitchMillimeter: 2.54,
  malePinWidthMillimeter: 0.64,
  defaultInsertionDepthMillimeter: 6,
  wireRadiusSceneUnit: 0.035,
});

const SIGNAL_COLORS = Object.freeze([
  "#2563eb",
  "#059669",
  "#7c3aed",
  "#ea580c",
  "#0891b2",
  "#db2777",
]);

const POWER_PINS = new Set(["5V", "3V3", "3.3V", "VCC", "VIN", "AUX_5V", "AUX_3V3"]);

export function oppositeGender(gender) {
  if (gender === ConnectorGender.MALE) return ConnectorGender.FEMALE;
  if (gender === ConnectorGender.FEMALE) return ConnectorGender.MALE;
  return null;
}

export function inferEndpointGender(componentKey, pinMetadata) {
  const metadataGender = pinMetadata?.connector?.gender;
  if (metadataGender === ConnectorGender.MALE || metadataGender === ConnectorGender.FEMALE) {
    return metadataGender;
  }

  if (componentKey?.startsWith("breadboard-") || componentKey?.startsWith("arduino-")) {
    return ConnectorGender.FEMALE;
  }

  return ConnectorGender.MALE;
}

export function inferWireColorRole(sourcePin, targetPin, sourceMetadata, targetMetadata) {
  const roles = [sourceMetadata?.electrical?.role, targetMetadata?.electrical?.role];
  if (roles.includes(WireColorRole.GROUND) || sourcePin?.includes("GND") || targetPin?.includes("GND")) {
    return WireColorRole.GROUND;
  }
  if (
    roles.includes(WireColorRole.POWER)
    || POWER_PINS.has(sourcePin)
    || POWER_PINS.has(targetPin)
  ) {
    return WireColorRole.POWER;
  }
  return WireColorRole.SIGNAL;
}

export function colorForWireRole(role, signalIndex = 0) {
  if (role === WireColorRole.POWER) return "#dc2626";
  if (role === WireColorRole.GROUND) return "#1f2937";
  return SIGNAL_COLORS[signalIndex % SIGNAL_COLORS.length];
}

export function getRouteOffset(index) {
  if (index === 0) return 0;
  const lane = Math.ceil(index / 2);
  return (index % 2 === 0 ? 1 : -1) * lane;
}

export function calculateCurveProfile(distance, heightDelta, routeIndex = 0) {
  const baseLift = Math.min(2.8, Math.max(0.65, distance * 0.2 + heightDelta * 0.35));
  return {
    lift: baseLift + Math.abs(getRouteOffset(routeIndex)) * 0.09,
    lateralOffset: getRouteOffset(routeIndex) * Math.min(0.22, Math.max(0.09, distance * 0.025)),
    tubularSegments: Math.max(28, Math.min(72, Math.round(distance * 9))),
  };
}

export function resolveJumperWire(connection, sourceEndpoint, targetEndpoint, signalIndex = 0) {
  const sourceRequiredGender = oppositeGender(sourceEndpoint.interfaceGender);
  const targetRequiredGender = oppositeGender(targetEndpoint.interfaceGender);
  const requestedSourceGender = connection.sourceConnector ?? sourceRequiredGender;
  const requestedTargetGender = connection.targetConnector ?? targetRequiredGender;
  const issues = [];

  if (!sourceRequiredGender || !targetRequiredGender) {
    issues.push({
      code: "UNKNOWN_CONNECTOR_GENDER",
      level: "error",
      message: "핀 커넥터 성별을 확인할 수 없습니다.",
    });
  }
  if (requestedSourceGender !== sourceRequiredGender) {
    issues.push({
      code: "SOURCE_GENDER_MISMATCH",
      level: "error",
      message: `${sourceEndpoint.pinKey}에는 ${sourceRequiredGender} 커넥터가 필요합니다.`,
    });
  }
  if (requestedTargetGender !== targetRequiredGender) {
    issues.push({
      code: "TARGET_GENDER_MISMATCH",
      level: "error",
      message: `${targetEndpoint.pinKey}에는 ${targetRequiredGender} 커넥터가 필요합니다.`,
    });
  }

  for (const [endpoint, connectorGender] of [
    [sourceEndpoint, requestedSourceGender],
    [targetEndpoint, requestedTargetGender],
  ]) {
    if (
      endpoint.kind === "breadboard-hole"
      && connectorGender !== ConnectorGender.MALE
    ) {
      issues.push({
        code: "BREADBOARD_REQUIRES_MALE_064",
        level: "error",
        message: "브레드보드 홀에는 0.64mm 수 핀만 삽입할 수 있습니다.",
      });
    }
    if (
      endpoint.kind === "breadboard-hole"
      && endpoint.connector?.diameterMillimeter
      && JUMPER_SPEC.malePinWidthMillimeter > endpoint.connector.diameterMillimeter
    ) {
      issues.push({
        code: "PIN_TOO_WIDE",
        level: "error",
        message: `${JUMPER_SPEC.malePinWidthMillimeter}mm 수 핀이 브레드보드 홀보다 큽니다.`,
      });
    }
  }

  const colorRole = inferWireColorRole(
    sourceEndpoint.pinKey,
    targetEndpoint.pinKey,
    sourceEndpoint.metadata,
    targetEndpoint.metadata,
  );

  return {
    ...connection,
    sourceConnector: requestedSourceGender,
    targetConnector: requestedTargetGender,
    wireType: `${requestedSourceGender}-${requestedTargetGender}`,
    colorRole,
    color: colorForWireRole(colorRole, signalIndex),
    validation: {
      valid: issues.every((issue) => issue.level !== "error"),
      issues,
    },
  };
}

export function createPinEndpoint(record, pinKey) {
  const metadata = record.asset?.metadata?.pins?.find((pin) => pin.pinKey === pinKey) ?? null;
  const componentKey = record.part.componentKey;
  return {
    placementId: record.part.id,
    componentKey,
    pinKey,
    kind: componentKey.startsWith("breadboard-")
      ? "breadboard-hole"
      : componentKey.startsWith("arduino-")
        ? "arduino-header"
        : "component-pin",
    interfaceGender: inferEndpointGender(componentKey, metadata),
    insertionDepthMillimeter:
      metadata?.mounting?.insertionDepthMillimeter
      ?? JUMPER_SPEC.defaultInsertionDepthMillimeter,
    outwardDirection: metadata?.outwardDirection ?? [0, 1, 0],
    connector: metadata?.connector ?? null,
    metadata,
  };
}
