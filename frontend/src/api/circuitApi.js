const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class CircuitGenerationError extends Error {
  constructor(detail, status) {
    const normalized = normalizeErrorDetail(detail, status);
    super(normalized.title);
    this.name = "CircuitGenerationError";
    this.status = status;
    this.code = normalized.code;
    this.title = normalized.title;
    this.reason = normalized.reason;
    this.suggestions = normalized.suggestions;
    this.rawMessage = normalized.rawMessage;
  }
}

function normalizeErrorDetail(detail, status) {
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    return {
      code: detail.code ?? `HTTP_${status}`,
      title: detail.title ?? "K-EXAONE 회로 생성에 실패했습니다.",
      reason: detail.reason ?? detail.rawMessage ?? "알 수 없는 오류가 발생했습니다.",
      suggestions: Array.isArray(detail.suggestions) ? detail.suggestions : defaultSuggestions,
      rawMessage: detail.rawMessage ?? "",
    };
  }

  return {
    code: `HTTP_${status}`,
    title: "K-EXAONE 회로 생성에 실패했습니다.",
    reason: detail || `K-EXAONE API 요청에 실패했습니다. (${status})`,
    suggestions: defaultSuggestions,
    rawMessage: detail || "",
  };
}

const defaultSuggestions = [
  "문장을 더 짧고 구체적으로 입력해보세요.",
  "지원 부품만 사용해보세요: LED, 버튼, 초음파 센서, 저항.",
  "잠시 후 다시 시도해보세요.",
];

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
    circuit: {
      ...response.circuit,
      assemblyPlan: response.assemblyPlan ?? response.assembly_plan ?? null,
    },
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

    throw new CircuitGenerationError(detail, response.status);
  }

  return normalizeCircuitResponse(await response.json(), prompt);
}
