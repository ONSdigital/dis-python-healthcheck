import dataclasses
from datetime import datetime
from enum import Enum


@dataclasses.dataclass
class CheckState:
    name: str
    status: HealthStatus
    status_code: int
    message: str
    stack_trace: Exception | None = None
    last_checked: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None

    def asdict(self) -> dict:
        result = {key: value for key, value in dataclasses.asdict(self).items() if value is not None}
        result["status"] = self.status.value

        for field in ("last_checked", "last_success", "last_failure"):
            if field in result:
                result[field] = result[field].isoformat().replace("+00:00", "Z")

        return result


@dataclasses.dataclass
class Version:
    language: str
    language_version: str
    version: str
    build_time: datetime | None = None
    git_commit: str | None = None


@dataclasses.dataclass
class HealthResponse:
    version: Version
    checks: list[CheckState]
    uptime: str | None = None
    start_time: datetime | None = None


class HealthStatus(Enum):
    HEALTHY = "OK"  # Component is working normally
    DEGRADED = "WARNING"  # Component works but with issues
    UNHEALTHY = "CRITICAL"  # Component is not working
