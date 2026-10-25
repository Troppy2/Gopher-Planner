import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# config.py -> core -> app -> backend -> repository root
REPO_ROOT = Path(__file__).resolve().parents[3]

# Load environment variables from Gopher-Planner/.env.
# Existing environment variables take precedence.
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    google_client_id: str
    frontend_origin: str
    jwt_secret: str
    cookie_secure: bool
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        frontend_origin = os.getenv(
            "FRONTEND_ORIGIN",
            "http://localhost:3000",
        ).strip().rstrip("/")
        jwt_secret = os.getenv("JWT_SECRET", "").strip()
        database_url = os.getenv("DATABASE_URL", "").strip()
        environment = os.getenv(
            "FLASK_ENVIRONMENT",
            "development",
        ).strip().lower()
        cookie_secure = (
            os.getenv("COOKIE_SECURE", "false").strip().lower() == "true"
        )

        missing = [
            name
            for name, value in (
                ("GOOGLE_CLIENT_ID", google_client_id),
                ("JWT_SECRET", jwt_secret),
            )
            if not value
        ]

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        if not database_url:
            if environment == "production":
                raise RuntimeError(
                    "DATABASE_URL is required in production."
                )

            # Store the local development database outside the source folders.
            instance_dir = Path(__file__).resolve().parents[2] / "instance"
            instance_dir.mkdir(parents=True, exist_ok=True)

            database_path = instance_dir / "dev.db"
            database_url = f"sqlite:///{database_path.as_posix()}"

        elif not (
            database_url.startswith("postgresql+psycopg://")
            or database_url.startswith("sqlite:///")
            or database_url == "sqlite://"
        ):
            raise RuntimeError(
                "DATABASE_URL must use postgresql+psycopg:// "
                "or sqlite:///"
            )

        return cls(
            google_client_id=google_client_id,
            frontend_origin=frontend_origin,
            jwt_secret=jwt_secret,
            cookie_secure=cookie_secure,
            database_url=database_url,
        )