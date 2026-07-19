import json
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.validator.adapter import convert_api_response_to_validator_json
from app.validator.rules import validate_and_attach


CircuitCase = Dict[str, Any]

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2]

RAW_CASE_DIR = PROJECT_ROOT / "data" / "validator_cases" / "raw"
CHECKED_CASE_DIR = PROJECT_ROOT / "data" / "validator_cases" / "checked"


def ensure_dirs() -> None:
    RAW_CASE_DIR.mkdir(parents=True, exist_ok=True)
    CHECKED_CASE_DIR.mkdir(parents=True, exist_ok=True)


def call_generate_api(prompt: str) -> CircuitCase:
    api_url = "http://127.0.0.1:8000/api/v1/circuit/generate"

    body = {
        "prompt": prompt
    }

    request = Request(
        api_url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(
            f"API 호출 실패: HTTP {error.code}\n{error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            "API 서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인하세요."
        ) from error

    data = json.loads(response_body)

    if not isinstance(data, dict):
        raise ValueError("API 응답 최상위 구조가 JSON object가 아닙니다.")

    data["userPrompt"] = prompt
    data["source"] = "/api/v1/circuit/generate"

    return data


def save_json(data: CircuitCase, folder: Path, case_name: str) -> Path:
    ensure_dirs()

    safe_name = case_name.replace(" ", "_").replace("/", "_")
    output_path = folder / f"{safe_name}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return output_path


def run_live_api_validation(case_name: str, prompt: str) -> None:
    print(f"\n=== {case_name} ===")
    print(f"[PROMPT] {prompt}")

    api_response = call_generate_api(prompt)
    raw_path = save_json(api_response, RAW_CASE_DIR, case_name)

    validator_input = convert_api_response_to_validator_json(api_response)
    checked_result = validate_and_attach(validator_input)
    checked_path = save_json(checked_result, CHECKED_CASE_DIR, case_name)

    print(f"[RAW 저장] {raw_path}")
    print(f"[CHECKED 저장] {checked_path}")

    print("\n[validationResults]")
    print(json.dumps(checked_result.get("validationResults", []), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_live_api_validation(
        case_name="live_led_blink_001",
        prompt="아두이노로 LED를 D9 핀에 연결해서 깜빡이는 회로를 만들어줘.",
    )