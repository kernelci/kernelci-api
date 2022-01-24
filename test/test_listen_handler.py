# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Alexandra Pereira <alexandra.pereira@collabora.com>

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


@pytest.fixture()
def mock_init_sub_id(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub._init_sub_id',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_listen(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.listen',
                 side_effect=async_mock)
    return async_mock


def test_listen_endpoint(mock_get_current_user,
                         mock_init_sub_id,
                         mock_listen):
    """
    Test Case : Test KernelCI API GET /listen endpoint for the
    positive path
    Expected Result :
        HTTP Response Code 200 OK
        Listen for events on a channel.
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user
    mock_listen.return_value = 'Listening for events on channel 1'
    with TestClient(app) as client:
        response = client.get(
            "/listen/1",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        assert response.status_code == 200


def test_listen_endpoint_not_found(mock_get_current_user,
                                   mock_init_sub_id,
                                   mock_listen):
    """
    Test Case : Test KernelCI API GET /listen endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 404 Not Found
        Channel not available or not subscribed to channel with an id
    """
    mock_listen.return_value = None

    with TestClient(app) as client:
        response = client.get(
            "/listen/1",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        assert response.status_code == 404


def test_listen_endpoint_without_token(mock_get_current_user,
                                       mock_init_sub_id,
                                       mock_listen):
    """
    Test Case : Test KernelCI API GET /listen endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 401 Unauthorized
        The request requires user authentication by token in header
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user
    mock_listen.return_value = 'Listening for events on channel 1'
    with TestClient(app) as client:
        response = client.get(
            "/listen/1",
            headers={
                "Accept": "application/json"
            },
        )
        assert response.status_code == 401
