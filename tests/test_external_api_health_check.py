from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from dis_python_healthcheck.external_api_healthcheck import ExternalAPIHealthCheck
from dis_python_healthcheck.models import HealthStatus

STATUS_OK = 200
STATUS_ERROR = 500


@pytest.mark.asyncio
async def test_check_returns_available(mocker):
    response = SimpleNamespace(
        status=STATUS_OK,
        json=AsyncMock(return_value={"version": "1.2"}),
        elapsed=timedelta(milliseconds=25),
    )

    response_context = MagicMock()
    response_context.__aenter__ = AsyncMock(return_value=response)
    response_context.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get.return_value = response_context

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)

    mocker.patch(
        "dis_python_healthcheck.external_api_healthcheck.aiohttp.ClientSession",
        return_value=session_context,
    )

    checker = ExternalAPIHealthCheck("http://localhost:8000", "dataset-api")
    result = await checker.check()

    assert result.status == HealthStatus.HEALTHY
    assert result.message == "dataset-api is ok"
    assert result.status_code == STATUS_OK
    assert checker.failure_count == 0


@pytest.mark.asyncio
async def test_check_returns_failure(mocker):
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(side_effect=RuntimeError("connection failed"))

    mocker.patch(
        "dis_python_healthcheck.external_api_healthcheck.aiohttp.ClientSession",
        return_value=session_context,
    )

    checker = ExternalAPIHealthCheck("http://localhost:8000", "dataset-api")

    result = await checker.check()

    assert result.status == HealthStatus.UNHEALTHY
    assert result.message == "connection failed"
    assert result.status_code == STATUS_ERROR
    assert checker.failure_count == 1


@pytest.mark.asyncio
async def test_check_circuit_breaker(mocker):
    response = SimpleNamespace(
        status=500,
        json=AsyncMock(return_value={"version": "1.2"}),
        elapsed=timedelta(milliseconds=25),
    )

    response_context = MagicMock()
    response_context.__aenter__ = AsyncMock(return_value=response)
    response_context.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get.return_value = response_context

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)

    mocker.patch(
        "dis_python_healthcheck.external_api_healthcheck.aiohttp.ClientSession",
        return_value=session_context,
    )

    checker = ExternalAPIHealthCheck("http://localhost:8000", "dataset-api")
    checker.circuit_open = True
    checker.last_failure_time = 100000000000
    with pytest.raises(Exception, match="Circuit breaker open for dataset-api"):
        await checker.check()

    assert checker.failure_count == 0
