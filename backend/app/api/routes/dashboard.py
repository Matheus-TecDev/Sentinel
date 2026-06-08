from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import viewer_access
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
dashboard_service = DashboardService()


@router.get("", response_model=DashboardSummary)
def dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(viewer_access),
) -> DashboardSummary:
    return dashboard_service.summary(db)
