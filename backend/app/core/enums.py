from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class ServiceEnvironment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class HealthStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
