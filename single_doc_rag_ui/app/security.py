from fastapi import Header, HTTPException

from app.config import get_settings


def require_admin_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()

    if not settings.admin_api_key:
        return

    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik API anahtarı.")