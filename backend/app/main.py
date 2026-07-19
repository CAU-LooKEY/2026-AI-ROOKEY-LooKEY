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
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            detail=(
                "K-EXAONE is not configured. Set K_EXAONE_API_KEY and "
                "K_EXAONE_ENDPOINT_ID in backend/.env."
            ),
        )

    try:
        return await KExaoneClient(settings).generate_circuit(request.prompt)
    except KExaoneError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
