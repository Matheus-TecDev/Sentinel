from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def get(self, db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    def get_by_email(self, db: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return db.execute(statement).scalar_one_or_none()

    def list(self, db: Session) -> list[User]:
        statement = select(User).order_by(User.name.asc())
        return list(db.execute(statement).scalars().all())

    def create(self, db: Session, data: dict) -> User:
        user = User(**data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update(self, db: Session, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
