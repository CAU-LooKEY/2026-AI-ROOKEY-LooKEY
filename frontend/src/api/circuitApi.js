const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function toPartCards(components = []) {
  return components.map((component, index) => ({
    title: `${index + 1}. ${component.name ?? component.label ?? component.id}`,
    desc: component.role ?? component.description ?? "회로 구성에 필요한 부품입니다.",
  }));
}

export function normalizeCircuitResponse(response, prompt) {
  const hasRequiredFields =
    response &&
    typeof response.title === "string" &&
    typeof response.code === "string" &&
    Array.isArray(response.components) &&
    response.circuit &&
    Array.isArray(response.circuit.parts) &&
    Array.isArray(response.circuit.connections);

  if (!hasRequiredFields) {
    throw new Error("K-EXAONE 응답에 필수 회로 데이터가 없습니다.");
  }

  const project = {
    title: response.title,
    difficulty: response.difficulty ?? "미정",
    estimatedTime: response.estimatedTime ?? response.estimated_time ?? "미정",
    parts: toPartCards(response.components),
    code: response.code,
    tutorSteps: response.tutorSteps ?? response.tutor_steps ?? [],
    shareMessage: response.shareMessage ?? `${response.title} 프로젝트를 공유합니다.`,
    warnings: Array.isArray(response.warnings) ? response.warnings : [],
    validationResults: response.validationResults ?? response.validation_results ?? [],
    unsupportedComponents: response.unsupportedComponents ?? response.unsupported_components ?? [],
  };

  return {
    prompt,
    project,
    circuit: response.circuit,
  };
}

export async function generateCircuit(prompt) {
  const response = await fetch(`${API_BASE_URL}/api/v1/circuit/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    let detail = "";
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? "";
    } catch {
      detail = "";
    }

    throw new Error(detail || `K-EXAONE API 요청에 실패했습니다. (${response.status})`);
  }

  return normalizeCircuitResponse(await response.json(), prompt);
}
