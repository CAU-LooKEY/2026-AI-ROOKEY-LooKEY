import arduinoUno from "../../assets/parts/arduino-uno-r3-top.png";
import sensor from "../../assets/parts/hc-sr04-top.png";
import led from "../../assets/parts/led-5mm-blue-top.png";
import button from "../../assets/parts/pushbutton-6x6-top.png";
import resistor from "../../assets/parts/resistor-220-ohm-top.png";
import pinData from "../../assets/all_component_pin_coordinates.json";

const partImages = {
  "arduino-uno-r3": arduinoUno,
  "hc-sr04": sensor,
  "led-5mm-blue": led,
  "pushbutton-6x6": button,
  "resistor-220-ohm": resistor,
};

const PART_LABELS = {
  "arduino-uno-r3": "Arduino Uno",
  "hc-sr04": "HC-SR04",
  "led-5mm-blue": "LED",
  "pushbutton-6x6": "푸시 버튼",
  "resistor-220-ohm": "220Ω",
};

const PART_LAYOUTS = {
  "arduino-uno-r3": {
    position: { x: 45, y: 135 },
    width: 230,
  },
  "hc-sr04": {
    position: { x: 430, y: 55 },
    width: 190,
  },
  "led-5mm-blue": {
    position: { x: 455, y: 305 },
    width: 68,
  },
  "pushbutton-6x6": {
    position: { x: 440, y: 205 },
    width: 82,
  },
  "resistor-220-ohm": {
    position: { x: 675, y: 330 },
    width: 125,
  },
};

const SIGNAL_COLORS = [
  "#2563eb",
  "#059669",
  "#7c3aed",
  "#ea580c",
  "#0891b2",
  "#db2777",
];

const VALID_CONNECTORS = new Set(["male", "female"]);

function makeNode(part, connectedPins, occurrence) {
  const component = pinData[part.componentKey];
  const layout = PART_LAYOUTS[part.componentKey];
  const offset = occurrence * 22;
  const width = layout?.width ?? part.width;
  const position = layout
    ? {
        x: layout.position.x + offset,
        y: layout.position.y + offset,
      }
    : part.position;

  return {
    id: part.id,
    type: "partNode",
    position,
    data: {
      label: PART_LABELS[part.componentKey] ?? part.label,
      componentKey: part.componentKey,
      image: partImages[part.componentKey],
      pins: component.pins.filter((pin) => connectedPins.has(pin.pin_key)),
      width,
      originalWidth: component.pixel_width,
      originalHeight: component.pixel_height,
    },
  };
}

function getPinPoint(nodes, nodeId, pinKey) {
  const node = nodes.find((item) => item.id === nodeId);
  const pin = node.data.pins.find((item) => item.pin_key === pinKey);
  const scale = node.data.width / node.data.originalWidth;

  return {
    x: node.position.x + pin.x_px * scale,
    y: node.position.y + pin.y_px * scale,
  };
}

function isGroundPin(pinKey) {
  return pinKey.includes("GND");
}

function isPowerPin(pinKey) {
  return ["5V", "3V3", "VCC", "VIN", "AUX_5V", "AUX_3V3"].includes(pinKey);
}

function getWireColor(connection, signalIndex) {
  if (isGroundPin(connection.sourcePin) || isGroundPin(connection.targetPin)) {
    return "#1f2937";
  }

  if (isPowerPin(connection.sourcePin) || isPowerPin(connection.targetPin)) {
    return "#dc2626";
  }

  return SIGNAL_COLORS[signalIndex % SIGNAL_COLORS.length];
}

function getRequiredWireConnector(componentKey) {
  // The Uno exposes female header sockets; the other supported parts expose pins/leads.
  return componentKey === "arduino-uno-r3" ? "male" : "female";
}

function getConnector(connection, field, componentKey) {
  return VALID_CONNECTORS.has(connection[field])
    ? connection[field]
    : getRequiredWireConnector(componentKey);
}

function getRouteOffset(index) {
  if (index === 0) return 0;
  const lane = Math.ceil(index / 2) * 18;
  return index % 2 === 0 ? lane : -lane;
}

function makeEdge(nodes, connection, index, signalIndex) {
  const sourceNode = nodes.find((item) => item.id === connection.source);
  const targetNode = nodes.find((item) => item.id === connection.target);
  const sourceConnector = getConnector(
    connection,
    "sourceConnector",
    sourceNode.data.componentKey,
  );
  const targetConnector = getConnector(
    connection,
    "targetConnector",
    targetNode.data.componentKey,
  );
  const wireType = connection.wireType ?? `${sourceConnector}-${targetConnector}`;
  const color = getWireColor(connection, signalIndex);
  const label = `${connection.sourcePin} ↔ ${connection.targetPin}`;

  return {
    id: connection.id,
    source: connection.source,
    sourceHandle: connection.sourcePin,
    target: connection.target,
    targetHandle: connection.targetPin,
    type: "pinEdge",
    data: {
      label,
      color,
      sourceConnector,
      targetConnector,
      wireType,
      routeOffset: getRouteOffset(index),
      labelPosition: 0.36 + (index % 3) * 0.14,
      sourcePoint: getPinPoint(nodes, connection.source, connection.sourcePin),
      targetPoint: getPinPoint(nodes, connection.target, connection.targetPin),
    },
  };
}

export function circuitToReactFlow(circuit) {
  const connectedPinsByPart = new Map(
    circuit.parts.map((part) => [part.id, new Set()]),
  );
  circuit.connections.forEach((connection) => {
    connectedPinsByPart.get(connection.source)?.add(connection.sourcePin);
    connectedPinsByPart.get(connection.target)?.add(connection.targetPin);
  });

  const occurrenceByComponent = new Map();
  const nodes = circuit.parts.map((part) => {
    const occurrence = occurrenceByComponent.get(part.componentKey) ?? 0;
    occurrenceByComponent.set(part.componentKey, occurrence + 1);
    return makeNode(
      part,
      connectedPinsByPart.get(part.id) ?? new Set(),
      occurrence,
    );
  });
  let signalIndex = 0;
  const edges = circuit.connections.map((connection, index) => {
    const isSignal = !(
      isGroundPin(connection.sourcePin)
      || isGroundPin(connection.targetPin)
      || isPowerPin(connection.sourcePin)
      || isPowerPin(connection.targetPin)
    );
    const edge = makeEdge(nodes, connection, index, signalIndex);
    if (isSignal) signalIndex += 1;
    return edge;
  });

  const jumpers = edges.map((edge) => ({
    id: edge.id,
    label: edge.data.label,
    color: edge.data.color,
    sourceConnector: edge.data.sourceConnector,
    targetConnector: edge.data.targetConnector,
    wireType: edge.data.wireType,
  }));

  return { nodes, edges, jumpers };
}
