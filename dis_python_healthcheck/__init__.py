import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from dis_python_logger import DisLogger, setup_logging

from dis_python_healthcheck.external_api_healthcheck import ExternalAPIHealthCheck as ExternalAPIHealthCheck
from dis_python_healthcheck.models import HealthStatus, Version

app_logging = setup_logging(__name__)

SCORE_THRESHOLD = 90


class HealthCheck:
    dis_logger = DisLogger(__name__, app_logging)

    def __init__(self, build_info: Version) -> None:
        self.start_time = datetime.now(UTC)
        self._started_monotonic = time.monotonic_ns()
        self.checks: dict[str, dict[str, Any]] = {}
        self._last_success: dict[str, str | None] = {}
        self._last_failure: dict[str, str | None] = {}
        self.version = build_info

    def register(self, name: str, uri: str, check_func: Any, timeout: float = 5.0, critical: bool = True) -> None:
        """Register a new health check."""
        self.checks[name] = {"func": check_func, "uri": uri, "timeout": timeout, "critical": critical}

    async def start(self, interval_seconds: float = 30.0) -> None:
        while True:
            await self.run_all_checks()
            await asyncio.sleep(interval_seconds)

    async def run_all_checks(self) -> dict[str, Any]:
        """Run all health checks and aggregate results."""
        # Run all checks concurrently
        tasks = [self.checks[name]["func"]() for name in self.checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        check_results = []
        overall_score = 100
        critical_failures = []

        for result in results:
            if isinstance(result, BaseException):
                continue

            if result.status == HealthStatus.HEALTHY:
                self._last_success[result.name] = result.last_success
                result.last_failure = self._last_failure.get(result.name)
                self.dis_logger.info("healthcheck ok", data=result.asdict())
            else:
                result.last_success = self._last_success.get(result.name)
                self._last_failure[result.name] = result.last_failure
                self.dis_logger.error("healthcheck failed", error=result.stack_trace, data=result.asdict())

            check_results.append(result.asdict())

            # Calculate score impact
            if result.status == HealthStatus.UNHEALTHY:
                check_config = self.checks[result.name]
                if check_config["critical"]:
                    overall_score -= 50
                    critical_failures.append(result.asdict())
                else:
                    overall_score -= 20

            elif result.status == HealthStatus.DEGRADED:
                overall_score -= 10

        # Ensure score doesn't go below 0
        overall_score = max(0, overall_score)

        # Determine overall status -
        if overall_score == SCORE_THRESHOLD:
            overall_status = HealthStatus.DEGRADED
        elif overall_score < SCORE_THRESHOLD:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "status": overall_status.value,
            "version": self.version,
            "uptime": time.monotonic_ns() - self._started_monotonic,
            "start_time": self.start_time.isoformat().replace("+00:00", "Z"),
            "checks": check_results,
        }
