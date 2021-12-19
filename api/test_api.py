# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

import pytest
from .main import app
from .models import User
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    """
    Test Case : Test KernelCI API root endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'message' key
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "KernelCI API"}


@pytest.fixture()
def mock_db_find_one(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.find_one',
                 side_effect=async_mock)
    return async_mock


def test_token_endpoint(mock_db_find_one):
    """
    Test Case : Test KernelCI API token endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'access_token' and 'token_type' key
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_db_find_one.return_value = user
    client = TestClient(app)
    response = client.post(
        "/token",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={'username': 'bob', 'password': 'hello'}
    )
    print("json", response.json())
    assert response.status_code == 200
    assert 'access_token' and 'token_type' in response.json()
