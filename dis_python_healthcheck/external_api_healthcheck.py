import time
from datetime import UTC, datetime

import aiohttp

from dis_python_healthcheck.models import CheckState, HealthStatus

STATUS_OK = 200


class ExternalAPIHealthCheck:
    """API health check with circuit breaker."""

    def __init__(self, api_url: str, api_name: str):
        self.api_url = api_url
        self.api_name = api_name
        self.circuit_open = False
        self.failure_count = 0
        self.retry_count = 3
        self.last_failure_time = 0.0
        self.last_success_time = 0.0
        self.circuit_timeout = 60  # seconds

    async def check(self) -> CheckState:
        # Check if circuit is open
        if self.circuit_open:
            if time.time() - self.last_failure_time > self.circuit_timeout:
                self.circuit_open = False
                self.failure_count = 0
            else:
                raise Exception(f"Circuit breaker open for {self.api_name}")

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(self.api_url, timeout=aiohttp.ClientTimeout(total=5)) as response,
            ):
                if response.status == STATUS_OK:
                    check_state = CheckState(
                        name=self.api_name,
                        status=HealthStatus.HEALTHY,
                        message=self.api_name + " is ok",
                        last_checked=datetime.now(UTC),
                        status_code=response.status,
                        last_success=datetime.now(UTC),
                    )
                    return check_state
                else:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    check_state = CheckState(
                        name=self.api_name,
                        status=HealthStatus.DEGRADED,
                        message=self.api_name + " functionality is unavailable or non-functioning",
                        last_checked=datetime.now(UTC),
                        status_code=response.status,
                        last_failure=datetime.now(UTC),
                    )

                    return check_state

        except Exception as e:
            # Update circuit breaker state
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.retry_count:
                self.circuit_open = True
            check_state = CheckState(
                name=self.api_name,
                status=HealthStatus.UNHEALTHY,
                last_checked=datetime.now(UTC),
                message=str(e),
                status_code=500,
                last_failure=datetime.now(UTC),
            )
            return check_state
