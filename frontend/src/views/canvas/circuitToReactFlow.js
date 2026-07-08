import arduinoUno from "../../assets/parts/arduino-uno-r3-top.png";
import sensor from "../../assets/parts/hc-sr04-top.png";
import led from "../../assets/parts/led-5mm-blue-top.png";
import resistor from "../../assets/parts/resistor-220-ohm-top.png";
import pinData from "../../assets/all_component_pin_coordinates.json";

const partImages = {
  "arduino-uno-r3": arduinoUno,
  "hc-sr04": sensor,
  "led-5mm-blue": led,
  "resistor-220-ohm": resistor,
};

function makeNode(part) {
  const component = pinData[part.componentKey];

  return {
    id: part.id,
    type: "partNode",
    position: part.position,
    data: {
      label: part.label,
      image: partImages[part.componentKey],
      pins: component.pins,
      width: part.width,
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

function makeEdge(nodes, connection) {
  return {
    id: connection.id,
    source: connection.source,
    target: connection.target,
    type: "pinEdge",
    data: {
      label: connection.label,
      labelDx: connection.labelDx ?? 0,
      labelDy: connection.labelDy ?? -14,
      color: connection.color ?? "#2563eb",
      sourcePoint: getPinPoint(nodes, connection.source, connection.sourcePin),
      targetPoint: getPinPoint(nodes, connection.target, connection.targetPin),
    },
  };
}

export function circuitToReactFlow(circuit) {
  const nodes = circuit.parts.map(makeNode);
  const edges = circuit.connections.map((connection) => makeEdge(nodes, connection));

  return { nodes, edges };
}
