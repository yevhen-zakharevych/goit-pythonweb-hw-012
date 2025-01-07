from unittest.mock import Mock

import pytest
from sqlalchemy import select

from src.db import User
from tests.conftest import TestingSessionLocal

user_data = {"username": "agent007@email.com", "password": "12345678"}


def test_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.services.email.send_email", mock_send_email)
    response = client.post("/signup", json=user_data)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["new_user"] == user_data["username"]
    assert "password" not in data


@pytest.mark.asyncio
async def test_login(client):
    user_data = {
        "username": "deadpool",
        "password": "12345678",
    }
    async with TestingSessionLocal() as session:
        current_user = await session.execute(select(User).where(User.username == user_data.get("username")))
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()

    response = client.post("/login",
                           data={"username": user_data.get("username"), "password": user_data.get("password")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data


def test_wrong_password_login(client):
    response = client.post("/login",
                           data={"username": "deadpool", "password": "password"})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Invalid password"


def test_wrong_username_login(client):
    response = client.post("login",
                           data={"username": "username", "password": "123455678"})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Invalid username"



