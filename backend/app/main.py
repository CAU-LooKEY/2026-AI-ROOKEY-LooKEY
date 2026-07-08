from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.circuit import router as circuit_router


app = FastAPI(
    title="LooKEY Backend API",
    description="Mock API for the Prompt-to-Circuit education service.",
    version="0.1.0",
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

app.include_router(circuit_router, prefix="/api/v1/circuit", tags=["circuit"])


@app.get("/")
def read_root():
    return {"service": "LooKEY Backend API", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
