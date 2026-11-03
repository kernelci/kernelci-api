# SPDX-License-Identifier: LGPL-2.1-or-later

"""Regression tests for pagination dependency registration and query parameters."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_pagination import add_pagination, paginate

from api.models import PageModel


@pytest.fixture
def pagination_client():
    """Register the API's pagination model without requiring a database."""
    app = FastAPI()

    @app.get("/items", response_model=PageModel[int])
    async def items():
        return paginate(list(range(200)))

    add_pagination(app)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "params, limit, offset",
    [({}, 50, 0), ({"limit": 150, "offset": 3}, 150, 3), ({"limit": 1}, 1, 0)],
)
def test_pagination_query_parameters(pagination_client, params, limit, offset):
    """Preserve defaults, offsets, and page sizes above the library's cap."""
    response = pagination_client.get("/items", params=params)

    assert response.status_code == 200
    assert response.json() == {
        "items": list(range(200))[offset : offset + limit],
        "total": 200,
        "limit": limit,
        "offset": offset,
    }


@pytest.mark.parametrize(
    "params, field",
    [
        ({"limit": 0}, "limit"),
        ({"limit": -1}, "limit"),
        ({"offset": -1}, "offset"),
        ({"limit": "invalid"}, "limit"),
    ],
)
def test_invalid_pagination_query_parameters(pagination_client, params, field):
    """Invalid pagination parameters remain request validation errors."""
    response = pagination_client.get("/items", params=params)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", field]


def test_pagination_openapi(pagination_client):
    """Expose optional query parameters with unchanged defaults and bounds."""
    response = pagination_client.get("/openapi.json")

    assert response.status_code == 200
    parameters = {
        param["name"]: param
        for param in response.json()["paths"]["/items"]["get"]["parameters"]
    }
    for name, default, minimum in [("limit", 50, 1), ("offset", 0, 0)]:
        parameter = parameters[name]
        assert parameter["in"] == "query"
        assert parameter["required"] is False
        assert parameter["schema"]["type"] == "integer"
        assert parameter["schema"]["default"] == default
        assert parameter["schema"]["minimum"] == minimum
        assert "maximum" not in parameter["schema"]
