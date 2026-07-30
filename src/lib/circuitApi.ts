import type { CircuitScene } from "../types/circuit";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

interface KExaoneCircuitPart {
  id: string;
  label: string;
  componentKey: string;
}

interface KExaoneCircuitConnection {
  id: string;
  source: string;
  sourcePin: string;
  target: string;
  targetPin: string;
  label: string;
  color: string;
}

interface KExaoneCircuitResponse {
  title: string;
  circuit: {
    parts: KExaoneCircuitPart[];
    connections: KExaoneCircuitConnection[];
  };
}

export class CircuitGenerationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CircuitGenerationError";
  }
}

const componentSlugAliases: Record<string, string> = {
  "led-5mm-blue": "led-5mm-red",
  "resistor-220-ohm": "resistor-220ohm",
};

const placementSlots = [
  { gridX: 3, gridY: 4 },
  { gridX: 10, gridY: 3 },
  { gridX: 14, gridY: 2 },
  { gridX: 10, gridY: 8 },
  { gridX: 15, gridY: 7 },
  { gridX: 5, gridY: 9 },
];

export async function generateCircuitScene(prompt: string): Promise<CircuitScene> {
  const response = await fetch(`${API_BASE_URL}/api/v1/circuit/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    throw new CircuitGenerationError(await resolveErrorMessage(response));
  }

  const data = (await response.json()) as KExaoneCircuitResponse;
  if (!data.circuit?.parts?.length || !Array.isArray(data.circuit.connections)) {
    throw new CircuitGenerationError("K-EXAONE 응답에 조립할 회로 정보가 없습니다.");
  }

  return toCircuitScene(data, prompt);
}

async function resolveErrorMessage(response: Response) {
  try {
    const body = await response.json();
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (detail?.reason) return detail.reason;
    if (detail?.title) return detail.title;
  } catch {
    // Fall through to the generic HTTP message.
  }
  return `K-EXAONE 요청에 실패했습니다. (${response.status})`;
}

function toCircuitScene(response: KExaoneCircuitResponse, prompt: string): CircuitScene {
  return {
    id: `k-exaone-${Date.now()}`,
    title: response.title,
    prompt,
    placements: response.circuit.parts.map((part, index) => ({
      id: part.id,
      componentSlug: componentSlugAliases[part.componentKey] ?? part.componentKey,
      ...placementSlots[index % placementSlots.length],
    })),
    connections: response.circuit.connections.map((connection) => ({
      id: connection.id,
      from: {
        placementId: connection.source,
        pinKey: connection.sourcePin,
      },
      to: {
        placementId: connection.target,
        pinKey: connection.targetPin,
      },
      color: connection.color,
      label: connection.label,
    })),
  };
}
