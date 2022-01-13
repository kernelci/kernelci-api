# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

import pytest
from api.main import app
from api.models import User
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock


@pytest.fixture()
def mock_get_current_user(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.auth.Authentication.get_current_user',
                 side_effect=async_mock)
    return async_mock


def test_me_endpoint(mock_get_current_user):
    """
    Test Case : Test KernelCI API /me endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with '_id', 'username', 'hashed_password'
        and 'active' keys
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user
    client = TestClient(app)
    response = client.get(
        "/me",
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer "
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
            "Edkp5M1S1AgYvX8VdB20"
        },
    )
    assert response.status_code == 200
    assert ('_id', 'username', 'hashed_password', 'active') == tuple(
                                                        response.json().keys())
