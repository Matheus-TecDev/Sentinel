import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.security import get_password_hash
from app.models.user import User

logger = logging.getLogger(__name__)


def seed_initial_admin(db: Session) -> None:
    settings = get_settings()
    existing = db.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL).first()
    if existing:
        return

    admin = User(
        name=settings.INITIAL_ADMIN_NAME,
        email=settings.INITIAL_ADMIN_EMAIL,
        password_hash=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Initial admin user created: %s", settings.INITIAL_ADMIN_EMAIL)
