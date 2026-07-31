import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    k_exaone_api_key: str = field(
        default_factory=lambda: os.getenv("K_EXAONE_API_KEY", "").strip(),
        repr=False,
    )
    k_exaone_endpoint_id: str = field(
        default_factory=lambda: os.getenv("K_EXAONE_ENDPOINT_ID", "").strip()
    )
    k_exaone_api_url: str = field(
        default_factory=lambda: os.getenv(
            "K_EXAONE_API_URL",
            "https://api.friendli.ai/dedicated/v1/chat/completions",
        ).strip()
    )
    k_exaone_timeout_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("K_EXAONE_TIMEOUT_SECONDS", "300")
        )
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.k_exaone_api_key and self.k_exaone_endpoint_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
