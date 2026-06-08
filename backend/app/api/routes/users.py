from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import admin_access
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserActivationUpdate, UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(admin_access),
) -> list[User]:
    return user_service.list(db)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_access),
) -> User:
    return user_service.create(db, payload)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_access),
) -> User:
    return user_service.update(db, user_id, payload)


@router.patch("/{user_id}/activation", response_model=UserRead)
def set_user_activation(
    user_id: int,
    payload: UserActivationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_access),
) -> User:
    return user_service.set_active(db, user_id, payload.is_active)
