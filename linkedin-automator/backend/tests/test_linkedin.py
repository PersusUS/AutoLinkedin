"""Tests for linkedin_publisher — M5.

Uses httpx mocking to test the publish logic without hitting LinkedIn.
Run: pytest tests/test_linkedin.py -v
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from services.linkedin_publisher import publish_post


@pytest.fixture
def mock_response():
    """Helper to create a mock httpx response."""
    def _make(status_code: int, headers: dict | None = None, text: str = ""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = headers or {}
        resp.text = text
        return resp
    return _make


class TestPublishBuildsCorrectBody:
    @pytest.mark.asyncio
    async def test_correct_body(self, mock_response):
        fake_resp = mock_response(
            201,
            headers={"x-restli-id": "urn:li:ugcPost:123456"},
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.linkedin_publisher.httpx.AsyncClient", return_value=mock_client):
            result = await publish_post(
                content="Test post content",
                access_token="fake_token",
                user_urn="AbC123",
            )

        assert result == "urn:li:ugcPost:123456"

        call_kwargs = mock_client.post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["author"] == "urn:li:person:AbC123"
        assert body["lifecycleState"] == "PUBLISHED"
        share = body["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert share["shareCommentary"]["text"] == "Test post content"
        assert share["shareMediaCategory"] == "NONE"

        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["X-Restli-Protocol-Version"] == "2.0.0"
        assert "Bearer fake_token" in headers["Authorization"]


class TestPublish401RaisesClearError:
    @pytest.mark.asyncio
    async def test_401_error(self, mock_response):
        fake_resp = mock_response(401, text="Unauthorized")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.linkedin_publisher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception, match="Token de LinkedIn expirado"):
                await publish_post(
                    content="Test",
                    access_token="expired_token",
                    user_urn="AbC123",
                )


class TestPublish422RaisesClearError:
    @pytest.mark.asyncio
    async def test_422_error(self, mock_response):
        fake_resp = mock_response(422, text="Unprocessable Entity")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.linkedin_publisher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception, match="Contenido inválido"):
                await publish_post(
                    content="x" * 5000,
                    access_token="valid_token",
                    user_urn="AbC123",
                )
