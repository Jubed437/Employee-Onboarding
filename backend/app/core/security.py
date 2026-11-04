import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.enums import Role

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-secret-change-me-32")
bearer = HTTPBearer()


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: Role
    team_id: str


def create_token(user: CurrentUser) -> str:
    payload = {
        "sub": user.id,
        "role": user.role.value,
        "teamId": user.team_id,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUser:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return CurrentUser(
            id=str(payload["sub"]),
            role=Role(payload["role"]),
            team_id=str(payload["teamId"]),
        )
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired bearer token"},
        ) from error


def require_roles(*roles: Role):
    def dependency(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Insufficient role permissions"},
            )
        return user

    return dependency
