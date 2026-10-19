import asyncio
import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from dis_python_healthcheck import ExternalAPIHealthCheck, HealthCheck
from dis_python_healthcheck.models import CheckState, HealthStatus, Version


@pytest_asyncio.fixture
async def healthcheck():
    external_api_check = ExternalAPIHealthCheck("bob", "bob_url")
    build_info = Version(
        language="python",
        language_version="3.14.3",
        version="0.1.0",
        build_time=datetime.datetime.now(),
        git_commit="0101010",
    )
    health_check = HealthCheck(build_info=build_info)
    health_check.register("test check", "http://localhost:8000", external_api_check.check)
    return health_check()


# Async fixtures
@pytest_asyncio.fixture
async def loaded_data():
    await asyncio.sleep(1)  # Simulate loading data asynchronously
    return {"key": "value"}


def test_register():
    external_api_check = ExternalAPIHealthCheck("bob", "bob_url")
    build_info = Version(
        language="python",
        language_version="3.14.3",
        version="0.1.0",
        build_time=datetime.datetime.now(),
        git_commit="0101010",
    )
    health_check = HealthCheck(build_info=build_info)
    health_check.register("test check", "http://localhost:8000", external_api_check.check)

    assert len(health_check.checks) == 1


@pytest.mark.asyncio
async def test_run_all_checks_healthy(mocker):
    checker = ExternalAPIHealthCheck("http://localhost:8000/health", "dataset-api")
    check_state = CheckState(
        name="dataset-api",
        status=HealthStatus.HEALTHY,
        status_code=200,
        message="dataset-api is ok",
    )
    check_mock = mocker.patch.object(
        checker,
        "check",
        new_callable=AsyncMock,
        return_value=check_state,
    )

    build_info = Version(
        language="python",
        language_version="3.14.3",
        version="0.1.0",
        build_time=datetime.datetime.now(),
        git_commit="0101010",
    )
    health_check = HealthCheck(build_info=build_info)
    health_check.register("dataset-api", "http://localhost:8000", checker.check)

    result = await health_check.run_all_checks()

    check_mock.assert_awaited_once_with()
    assert result["checks"][0]["name"] == "dataset-api"
    assert result["status"] == "OK"


@pytest.mark.asyncio
async def test_run_all_checks_unhealthy(mocker):
    checker = ExternalAPIHealthCheck("http://localhost:8000/health", "dataset-api")
    check_state = CheckState(
        name="dataset-api",
        status=HealthStatus.UNHEALTHY,
        status_code=500,
        message="dataset-api is not ok",
        last_failure=datetime.datetime.now(),
    )
    check_mock = mocker.patch.object(
        checker,
        "check",
        new_callable=AsyncMock,
        return_value=check_state,
    )

    build_info = Version(
        language="python",
        language_version="3.14.3",
        version="0.1.0",
        build_time=datetime.datetime.now(),
        git_commit="0101010",
    )
    health_check = HealthCheck(build_info=build_info)
    health_check.register("dataset-api", "http://localhost:8000", checker.check)

    result = await health_check.run_all_checks()

    check_mock.assert_awaited_once_with()

    assert result["status"] == "CRITICAL"
    assert result["checks"][0]["name"] == "dataset-api"


@pytest.mark.asyncio
async def test_run_all_checks_degraded(mocker):
    checker = ExternalAPIHealthCheck("http://localhost:8000/health", "dataset-api")
    check_state = CheckState(
        name="dataset-api",
        status=HealthStatus.DEGRADED,
        status_code=429,
        message="dataset-api is not ok",
        last_failure=datetime.datetime.now(),
    )
    check_mock = mocker.patch.object(
        checker,
        "check",
        new_callable=AsyncMock,
        return_value=check_state,
    )

    build_info = Version(
        language="python",
        language_version="3.14.3",
        version="0.1.0",
        build_time=datetime.datetime.now(),
        git_commit="0101010",
    )
    health_check = HealthCheck(build_info=build_info)
    health_check.register("dataset-api", "http://localhost:8000", checker.check)

    result = await health_check.run_all_checks()

    check_mock.assert_awaited_once_with()

    assert result["status"] == "WARNING"
    assert result["checks"][0]["name"] == "dataset-api"
