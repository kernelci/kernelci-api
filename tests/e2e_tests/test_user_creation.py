# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""End-to-end test functions for KernelCI API user creation"""

import json
import pytest

from api.models import User
from api.db import Database
from api.auth import Authentication
from .conftest import db_create


@pytest.mark.dependency(
    depends=["tests/e2e_tests/test_user_group_handler.py::test_create_user_groups"],
    scope="session")
@pytest.mark.dependency()
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_create_admin_user(test_async_client):
    """
    Test Case : Get hashed password using authentication method to create an admin
    user. Create the admin user using database create method.
    Request authentication token using '/user/login' endpoint for the user and
    store it in pytest global variable 'ADMIN_BEARER_TOKEN'.
    """
    username = 'admin'
    password = 'test'
    hashed_password = Authentication.get_password_hash(password)

    obj = await db_create(
        Database.COLLECTIONS[User],
        User(
            username=username,
            hashed_password=hashed_password,
            email='test-admin@kernelci.org',
            groups=[],
            is_superuser=1,
            is_verified=1
        ))
    assert obj is not None

    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data=f"username={username}&password={password}"
    )
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().keys() == {
        'access_token',
        'token_type',
    }
    pytest.ADMIN_BEARER_TOKEN = response.json()['access_token']


@pytest.mark.dependency(depends=["test_create_admin_user"])
@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_create_regular_user(test_async_client):
    """
    Test Case : Test KernelCI API '/user/register' endpoint to create regular
    user when requested with admin user's bearer token. Request '/user/login'
    endpoint for the user and store it in pytest global variable 'BEARER_TOKEN'.
    """
    username = 'test_user'
    password = 'test'
    email = 'test@kernelci.org'
    response = await test_async_client.post(
        "user/register",
        headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {pytest.ADMIN_BEARER_TOKEN}"
            },
        data=json.dumps({
            'username': username,
            'password': password,
            'email': email
        })
    )
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser', 'is_verified',
            'username', 'groups') == tuple(response.json().keys())

    # User needs to verified before getting access token
    # Directly updating user to by pass user verification via email
    user_id = response.json()['id']
    response = await test_async_client.patch(
        f"user/{user_id}",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {pytest.ADMIN_BEARER_TOKEN}"
        },
        data=json.dumps({"is_verified": True})
    )
    assert response.status_code == 200

    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data=f"username={username}&password={password}"
    )
    assert response.status_code == 200
    assert response.json().keys() == {
        'access_token',
        'token_type',
    }
    pytest.BEARER_TOKEN = response.json()['access_token']


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_create_regular_user"])
async def test_whoami(test_async_client):
    """
    Test Case : Test KernelCI API /whoami endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'email', username', 'groups', 'is_superuser'
        'is_verified' and 'is_active' keys
    """
    response = await test_async_client.get(
        "whoami",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
    )
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser', 'is_verified',
            'username', 'groups') == tuple(response.json().keys())
    assert response.json()['username'] == 'test_user'


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_create_regular_user"])
async def test_create_user_negative(test_async_client):
    """
    Test Case : Test KernelCI API /user/register endpoint when requested
    with regular user's bearer token.
    Expected Result :
        HTTP Response Code 403 Forbidden
        JSON with 'detail' key denoting 'Forbidden' error
    """
    response = await test_async_client.post(
        "user/register",
        headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
            },
        data=json.dumps({
            'username': 'test',
            'password': 'test',
            'email': 'test@kernelci.org'
        })
    )
    assert response.status_code == 403
    assert response.json() == {'detail': 'Forbidden'}
