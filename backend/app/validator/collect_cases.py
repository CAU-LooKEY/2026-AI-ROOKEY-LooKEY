"""
LOOKEY 3팀 — collect_cases.py

역할:
1. 다른 팀이 만든 K-EXAONE 회로 생성 결과 JSON을 가져온다.
2. 가져온 자료를 validator가 검사할 수 있는 형태로 저장한다.
3. Edge Case 수집을 위한 원본 데이터를 관리한다.

주의:
- 이 파일은 회로를 직접 검증하는 파일이 아니다.
- 검증은 rules.py의 validate_and_attach()가 담당한다.
- 이 파일은 '검사할 자료를 가져오는 역할'만 한다.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import Request, urlopen


CircuitCase = Dict[str, Any]


# 프로젝트 루트 기준 저장 폴더
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2]

# 수집한 K-EXAONE 결과를 저장할 폴더
RAW_CASE_DIR = PROJECT_ROOT / "data" / "validator_cases" / "raw"

# validator로 검사한 뒤 결과를 붙인 파일을 저장할 폴더
CHECKED_CASE_DIR = PROJECT_ROOT / "data" / "validator_cases" / "checked"


def ensure_case_dirs() -> None:
    """자료 저장 폴더가 없으면 생성한다."""
    RAW_CASE_DIR.mkdir(parents=True, exist_ok=True)
    CHECKED_CASE_DIR.mkdir(parents=True, exist_ok=True)


def load_case_from_file(file_path: str) -> CircuitCase:
    """
    로컬 JSON 파일에서 검사할 회로 자료를 가져온다.

    예:
    load_case_from_file("sample_kexaone_result.json")
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("회로 케이스 JSON의 최상위 구조는 dict/object여야 합니다.")

    return data


def load_cases_from_folder(folder_path: str) -> List[CircuitCase]:
    """
    폴더 안에 있는 여러 JSON 파일을 한 번에 가져온다.

    예:
    load_cases_from_folder("backend/app/validator/sample_cases")
    """
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder_path}")

    cases: List[CircuitCase] = []

    for json_file in folder.glob("*.json"):
        try:
            case = load_case_from_file(str(json_file))
            case["_source_file"] = str(json_file)
            cases.append(case)
        except Exception as error:
            print(f"[SKIP] {json_file.name}: {error}")

    return cases


def load_case_from_api(api_url: str) -> CircuitCase:
    """
    다른 팀 백엔드 API에서 검사할 회로 JSON을 가져온다.

    예:
    load_case_from_api("http://127.0.0.1:8000/api/v1/circuit/demo")
    """
    request = Request(
        api_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "LOOKEY-Validator-Collector",
        },
        method="GET",
    )

    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")

    data = json.loads(body)

    if not isinstance(data, dict):
        raise ValueError("API 응답 JSON의 최상위 구조는 dict/object여야 합니다.")

    return data


def save_raw_case(case_data: CircuitCase, case_name: str) -> Path:
    """
    가져온 원본 회로 JSON을 raw 폴더에 저장한다.

    예:
    save_raw_case(case, "ultrasonic_led_001")
    """
    ensure_case_dirs()

    safe_name = case_name.replace(" ", "_").replace("/", "_")
    output_path = RAW_CASE_DIR / f"{safe_name}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(case_data, file, ensure_ascii=False, indent=2)

    return output_path


def save_checked_case(case_data: CircuitCase, case_name: str) -> Path:
    """
    validator 검사 결과가 붙은 JSON을 checked 폴더에 저장한다.
    """
    ensure_case_dirs()

    safe_name = case_name.replace(" ", "_").replace("/", "_")
    output_path = CHECKED_CASE_DIR / f"{safe_name}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(case_data, file, ensure_ascii=False, indent=2)

    return output_path


def collect_from_api(api_url: str, case_name: str) -> Path:
    """
    API에서 K-EXAONE 생성 결과를 가져와 raw JSON으로 저장한다.
    """
    case_data = load_case_from_api(api_url)
    saved_path = save_raw_case(case_data, case_name)

    print(f"[OK] API에서 자료를 가져와 저장했습니다: {saved_path}")
    return saved_path


def collect_from_file(file_path: str, case_name: str) -> Path:
    """
    로컬 JSON 파일에서 자료를 가져와 raw JSON으로 저장한다.
    """
    case_data = load_case_from_file(file_path)
    saved_path = save_raw_case(case_data, case_name)

    print(f"[OK] 파일에서 자료를 가져와 저장했습니다: {saved_path}")
    return saved_path


def summarize_case(case_data: CircuitCase) -> Dict[str, Any]:
    """
    가져온 회로 자료를 간단히 요약한다.
    Edge Case 정리할 때 빠르게 확인하기 위한 용도.
    """
    nodes = case_data.get("nodes", [])
    edges = case_data.get("edges", [])
    code = case_data.get("code", "")

    return {
        "id": case_data.get("id"),
        "title": case_data.get("title"),
        "userPrompt": case_data.get("userPrompt") or case_data.get("prompt"),
        "node_count": len(nodes) if isinstance(nodes, list) else 0,
        "edge_count": len(edges) if isinstance(edges, list) else 0,
        "has_code": isinstance(code, str) and bool(code.strip()),
        "warnings": case_data.get("warnings", []),
        "safety_focus": case_data.get("safety_focus", []),
    }


if __name__ == "__main__":
    FILE_PATH = "backend/app/validator/sample_cases/kexaone_result_001.json"
    CASE_NAME = "kexaone_result_001"

    try:
        collected_case = load_case_from_file(FILE_PATH)
        saved = save_raw_case(collected_case, CASE_NAME)

        print("[OK] 검사할 자료 수집 완료")
        print(f"저장 위치: {saved}")
        print("\n[요약]")
        print(json.dumps(summarize_case(collected_case), ensure_ascii=False, indent=2))

    except Exception as error:
        print("[ERROR] 자료 수집 실패")
        print(error)