from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRead


class AuthService:
    def __init__(self) -> None:
        self.users = UserRepository()

    def login(self, db: Session, payload: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(db, payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")
        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenResponse(access_token=token, user=UserRead.model_validate(user))
