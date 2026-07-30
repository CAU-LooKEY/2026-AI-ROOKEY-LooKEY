from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.settings import get_settings
from app.schemas.circuit import CircuitGenerateRequest, CircuitGenerationResponse
from app.services.k_exaone import KExaoneClient, KExaoneError


app = FastAPI(
    title="LooKEY Backend API",
    description="K-EXAONE circuit generation API for the LooKEY education service.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_generation_error_detail(error: str) -> dict:
    normalized = error.lower()
    if "timed out" in normalized:
        return {
            "code": "K_EXAONE_TIMEOUT",
            "title": "K-EXAONE 응답을 받지 못했습니다.",
            "reason": "설정된 대기 시간 안에 AI 응답이 도착하지 않았습니다.",
            "suggestions": [
                "문장을 더 짧고 구체적으로 입력해보세요.",
                "지원 부품만 사용해보세요: LED, 버튼, 초음파 센서, 저항, 서보 모터.",
                "잠시 후 다시 시도해보세요.",
            ],
            "rawMessage": error,
        }
    if "schema" in normalized or "validation" in normalized:
        return {
            "code": "K_EXAONE_SCHEMA_ERROR",
            "title": "K-EXAONE 응답 형식이 회로 스키마와 맞지 않습니다.",
            "reason": "AI가 지원하지 않는 부품, 잘못된 핀 이름, 중복 핀 연결 중 하나를 만들었을 가능성이 큽니다.",
            "suggestions": [
                "부품 이름을 명확히 적어보세요. 예: Arduino UNO, LED, 220옴 저항.",
                "동작을 한 문장으로 단순하게 줄여 다시 시도해보세요.",
                "같은 Arduino 핀을 여러 부품에 연결하는 요청은 피해주세요.",
            ],
            "rawMessage": error,
        }
    if "connect" in normalized:
        return {
            "code": "K_EXAONE_CONNECTION_ERROR",
            "title": "K-EXAONE API에 연결하지 못했습니다.",
            "reason": "네트워크, API URL, endpoint 설정 중 하나를 확인해야 합니다.",
            "suggestions": [
                "인터넷 연결 상태를 확인해주세요.",
                "backend/.env의 K_EXAONE_API_URL과 endpoint ID를 확인해주세요.",
                "잠시 후 다시 시도해보세요.",
            ],
            "rawMessage": error,
        }
    return {
        "code": "K_EXAONE_ERROR",
        "title": "K-EXAONE 회로 생성에 실패했습니다.",
        "reason": error,
        "suggestions": [
            "문장을 더 짧게 입력해보세요.",
            "지원 부품만 사용해보세요: LED, 버튼, 초음파 센서, 저항.",
            "잠시 후 다시 시도해보세요.",
        ],
        "rawMessage": error,
    }


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "aiProvider": "K-EXAONE",
        "aiConfigured": settings.is_configured,
    }


@app.post(
    "/api/v1/circuit/generate",
    response_model=CircuitGenerationResponse,
    response_model_by_alias=True,
)
async def generate_circuit(request: CircuitGenerateRequest):
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "K_EXAONE_NOT_CONFIGURED",
                "title": "K-EXAONE 설정이 없습니다.",
                "reason": "backend/.env에 API 키와 endpoint ID가 설정되어 있지 않습니다.",
                "suggestions": [
                    "K_EXAONE_API_KEY 값을 확인해주세요.",
                    "K_EXAONE_ENDPOINT_ID 값을 확인해주세요.",
                    "백엔드 서버를 재시작해주세요.",
                ],
            },
        )

    try:
        return await KExaoneClient(settings).generate_circuit(request.prompt)
    except KExaoneError as exc:
        raise HTTPException(
            status_code=502,
            detail=build_generation_error_detail(str(exc)),
        ) from exc
