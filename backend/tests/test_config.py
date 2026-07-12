import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_incident_failure_threshold_defaults_to_three() -> None:
    settings = Settings(_env_file=None)

    assert settings.INCIDENT_FAILURE_THRESHOLD == 3


@pytest.mark.parametrize("threshold", [0, -1])
def test_incident_failure_threshold_rejects_values_below_one(threshold: int) -> None:
    with pytest.raises(ValidationError):
        Settings(INCIDENT_FAILURE_THRESHOLD=threshold, _env_file=None)
