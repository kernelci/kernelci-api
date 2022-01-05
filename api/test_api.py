# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

import pytest
from .main import app
from .models import User
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from .pubsub import Subscription


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
    assert ('_id' and 'username' and 'hashed_password' and
            'active') in response.json()


def test_token_endpoint_incorrect_password(mock_db_find_one):
    """
    Test Case : Test KernelCI API token endpoint for negative path
    Incorrect password should be passed to the endpoint

    Expected Result :
        HTTP Response Code 401 Unauthorized
        JSON with 'detail' key
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_db_find_one.return_value = user
    client = TestClient(app)

    # Pass incorrect password
    response = client.post(
        "/token",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={'username': 'bob', 'password': 'hi'}
    )
    print("response json", response.json())
    assert response.status_code == 401
    assert response.json() == {'detail': 'Incorrect username or password'}


@pytest.fixture()
def mock_init_sub_id(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub._init_sub_id',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_subscribe(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.subscribe',
                 side_effect=async_mock)
    return async_mock


def test_subscribe_endpoint(mock_get_current_user, mock_init_sub_id,
                            mock_subscribe):
    """
    Test Case : Test KernelCI API /subscribe endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id' and 'channel' keys
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    subscribe = Subscription(id=1, channel='abc')
    mock_subscribe.return_value = subscribe

    with TestClient(app) as client:
        # Use context manager to trigger a startup event on the app object
        response = client.post(
            "/subscribe/abc",
            headers={
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        print("response.json()", response.json())
        assert response.status_code == 200
        assert ('id' and 'channel') in response.json()
