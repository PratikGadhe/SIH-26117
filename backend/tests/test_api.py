import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


async def send_request(method: str, path: str) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path)


def test_versioned_api_router_is_registered() -> None:
    response = asyncio.run(send_request("GET", "/api/v1"))

    assert response.status_code == 200
    assert response.json() == {
        "name": "Cognivault API",
        "version": "v1",
    }


def test_unsupported_api_method_returns_structured_error() -> None:
    response = asyncio.run(send_request("POST", "/api/v1"))

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Method Not Allowed"}


def test_unknown_api_route_returns_structured_error() -> None:
    response = asyncio.run(send_request("GET", "/api/v1/not-found"))

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}


def test_openapi_documentation_lists_only_implemented_endpoints() -> None:
    response = asyncio.run(send_request("GET", "/openapi.json"))

    assert response.status_code == 200
    assert set(response.json()["paths"]) == {
        "/health",
        "/api/v1",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/audit",
        "/api/v1/agent/run",
        "/api/v1/authorization-demo/admin",
        "/api/v1/authorization-demo/operations",
        "/api/v1/system/status",
    }


def test_openapi_documents_bearer_authentication() -> None:
    response = asyncio.run(send_request("GET", "/openapi.json"))

    document = response.json()
    security_schemes = document["components"]["securitySchemes"]
    assert security_schemes["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }
    assert document["paths"]["/api/v1/auth/me"]["get"]["security"] == [
        {"HTTPBearer": []}
    ]
    for path in (
        "/api/v1/authorization-demo/admin",
        "/api/v1/authorization-demo/operations",
        "/api/v1/audit",
    ):
        assert document["paths"][path]["get"]["security"] == [{"HTTPBearer": []}]
    assert document["paths"]["/api/v1/agent/run"]["post"]["security"] == [
        {"HTTPBearer": []}
    ]


def test_swagger_documentation_is_available() -> None:
    response = asyncio.run(send_request("GET", "/docs"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
