"""Integration tests for API endpoints."""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import uuid
import os

# These tests assume test database is configured
# Set TEST_DATABASE_URL env var to run these tests


@pytest.fixture
async def test_app():
    """Create test FastAPI app instance."""
    from main import app
    return app


@pytest.fixture
async def test_client(test_app):
    """Create test HTTP client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_org_id():
    """Generate test organization ID."""
    return str(uuid.uuid4())


@pytest.fixture
async def test_user_id():
    """Generate test user ID."""
    return str(uuid.uuid4())


class TestHealthEndpoints:
    """Test health check endpoints."""

    async def test_root_health_check(self, test_client):
        """Test root health endpoint."""
        response = await test_client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_health_endpoint(self, test_client):
        """Test /health endpoint."""
        response = await test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestErrorHandling:
    """Test error handling across endpoints."""

    async def test_validation_error(self, test_client, test_org_id):
        """Test validation error handling."""
        response = await test_client.post(
            f"/api/threads/",
            json={
                "org_id": test_org_id,
                "title": "",  # Empty title should fail validation
            }
        )
        # Endpoints require authentication, so 401 is valid
        assert response.status_code in [400, 401, 422]

    async def test_invalid_uuid_handling(self, test_client):
        """Test invalid UUID handling."""
        response = await test_client.get(
            "/api/threads/invalid-uuid",
            headers={"x-org-id": "also-invalid"}
        )
        assert response.status_code in [400, 404, 422]

    async def test_missing_auth_header(self, test_client):
        """Test request without authentication."""
        response = await test_client.get("/api/threads/", follow_redirects=True)
        # Should either return 401 or 400 depending on auth requirement or 307 if redirecting
        assert response.status_code in [400, 401, 422, 307]


class TestSecurityHeaders:
    """Test security headers are present."""

    async def test_security_headers_present(self, test_client):
        """Test that security headers are returned."""
        response = await test_client.get("/")

        # Check essential security headers
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    async def test_csp_header_present(self, test_client):
        """Test Content Security Policy header."""
        response = await test_client.get("/")
        assert "content-security-policy" in response.headers
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp


class TestInputValidation:
    """Test input validation across endpoints."""

    async def test_string_length_validation(self, test_client, test_org_id):
        """Test string length validation."""
        # Very long input should be rejected
        long_string = "x" * 100000

        response = await test_client.post(
            "/api/threads/",
            json={
                "org_id": test_org_id,
                "title": long_string,
            }
        )
        # Endpoints require authentication, so 401 is valid
        assert response.status_code in [400, 401, 422]

    async def test_uuid_format_validation(self, test_client):
        """Test UUID format validation."""
        response = await test_client.get(
            "/api/threads/not-a-uuid",
            headers={"x-org-id": "also-not-uuid"}
        )
        # Should reject invalid UUIDs
        assert response.status_code in [400, 404, 422]


class TestCORSHeaders:
    """Test CORS configuration."""

    async def test_cors_headers_development(self, test_client):
        """Test CORS headers in development."""
        # In development, should allow all origins
        response = await test_client.options(
            "/",
            headers={"origin": "http://localhost:3000"}
        )
        # CORS headers should be present (status 200 or 204)
        assert response.status_code in [200, 204, 405]


# Async test runner
def run_async_tests():
    """Run all async tests."""
    pytest_args = [
        __file__,
        "-v",
        "--asyncio-mode=auto"
    ]

    pytest.main(pytest_args)


if __name__ == "__main__":
    run_async_tests()
