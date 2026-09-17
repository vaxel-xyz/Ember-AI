import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import Settings, get_settings

_scheme = HTTPBearer(auto_error=False)


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_scheme),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    if not secrets.compare_digest(credentials.credentials.encode(), settings.ember_api_key.encode()):
        raise HTTPException(status_code=403, detail="Invalid API key")
