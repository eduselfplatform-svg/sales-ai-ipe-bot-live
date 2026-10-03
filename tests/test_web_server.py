import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
import telegram
from telegram import Update

import config
import main


@pytest.fixture
def mock_bot_environment():
    config.BOT_TOKEN = "123456:FAKE_TOKEN_FOR_TESTS"
    config.RUN_MODE = "polling"
    config.PORT = 8080
    config.WEBHOOK_SECRET = ""

    mock_app = MagicMock()
    mock_app.running = True
    mock_app.bot = MagicMock()
    mock_app.bot.defaults.tzinfo = None
    mock_app.update_queue = asyncio.Queue()
    mock_app.updater = MagicMock()
    mock_app.updater.running = True

    with patch.object(main, "ptb_app", mock_app):
        yield mock_app



def test_health_check_endpoint(mock_bot_environment):
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["bot_running"] is True


def test_root_endpoint(mock_bot_environment):
    client = TestClient(main.app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "IPE School" in data["service"]


def test_token_get_check(mock_bot_environment):
    client = TestClient(main.app)
    # To'g'ri token
    res_valid = client.get(f"/{config.BOT_TOKEN}")
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "ok"

    # Noto'g'ri token
    res_invalid = client.get("/wrong_token_123")
    assert res_invalid.status_code == 404


def test_telegram_webhook_post(mock_bot_environment):
    client = TestClient(main.app)
    payload = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": 1600000000,
            "chat": {"id": 12345, "type": "private"},
            "from": {"id": 12345, "is_bot": False, "first_name": "TestUser"},
            "text": "Salom test"
        }
    }

    # Noto'g'ri token bilan POST
    res_forbidden = client.post("/wrong_token", json=payload)
    assert res_forbidden.status_code == 403

    # To'g'ri token bilan POST
    res_ok = client.post(f"/{config.BOT_TOKEN}", json=payload)
    assert res_ok.status_code == 200
    assert not mock_bot_environment.update_queue.empty()


def test_telegram_webhook_alt_post(mock_bot_environment):
    client = TestClient(main.app)
    payload = {
        "update_id": 999998,
        "message": {
            "message_id": 2,
            "date": 1600000000,
            "chat": {"id": 12345, "type": "private"},
            "from": {"id": 12345, "is_bot": False, "first_name": "TestUser"},
            "text": "Salom test alt"
        }
    }

    res_ok = client.post("/webhook", json=payload)
    assert res_ok.status_code == 200
    assert not mock_bot_environment.update_queue.empty()
