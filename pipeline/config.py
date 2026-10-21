import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://secop:secop@localhost:5432/secop")
    # SECOP II - Contratos Electrónicos (datos.gov.co, Socrata API)
    dataset_url: str = os.getenv("SECOP_DATASET_URL", "https://www.datos.gov.co/resource/jbjy-vk9h.json")
    # Optional: a free Socrata app token raises the rate limit (https://dev.socrata.com/docs/app-tokens.html)
    app_token: str | None = os.getenv("SOCRATA_APP_TOKEN") or None
    page_size: int = int(os.getenv("PAGE_SIZE", "5000"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "60"))


settings = Settings()
