from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self) -> None:
        self.users = UserRepository()

    def list(self, db: Session) -> list[User]:
        return self.users.list(db)

    def create(self, db: Session, payload: UserCreate) -> User:
        if self.users.get_by_email(db, payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")
        data = payload.model_dump()
        password = data.pop("password")
        data["password_hash"] = get_password_hash(password)
        return self.users.create(db, data)

    def update(self, db: Session, user_id: int, payload: UserUpdate) -> User:
        user = self._get_or_404(db, user_id)
        data = payload.model_dump(exclude_unset=True)
        if "email" in data:
            existing = self.users.get_by_email(db, data["email"])
            if existing and existing.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        return self.users.update(db, user, data)

    def set_active(self, db: Session, user_id: int, is_active: bool) -> User:
        user = self._get_or_404(db, user_id)
        return self.users.update(db, user, {"is_active": is_active})

    def _get_or_404(self, db: Session, user_id: int) -> User:
        user = self.users.get(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        return user
