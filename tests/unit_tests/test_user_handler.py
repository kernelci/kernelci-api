# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022, 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API user handler"""

import json
import pytest

from tests.unit_tests.conftest import (
    ADMIN_BEARER_TOKEN,
    BEARER_TOKEN,
)
from api.models import UserGroup
from api.user_models import UserRead


@pytest.mark.asyncio
async def test_create_regular_user(mock_db_create, mock_publish_cloudevent,
                                   test_async_client):
    """
    Test Case : Test KernelCI API /user/register endpoint to create regular
    user when requested with admin user's bearer token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'email', 'groups', 'is_active'
        'is_verified' and 'is_superuser' keys
    """
    user = UserRead(
        id='65265305c74695807499037f',
        username='test',
        email='test@kernelci.org',
        groups=[],
        is_active=True,
        is_verified=False,
        is_superuser=False
    )
    mock_db_create.return_value = user

    response = await test_async_client.post(
        "user/register",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({
            'username': 'test',
            'password': 'test',
            'email': 'test@kernelci.org'
        })
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser', 'is_verified',
            'username', 'groups') == tuple(response.json().keys())


@pytest.mark.asyncio
async def test_create_admin_user(  # pylint: disable=too-many-arguments
                           mock_db_create, mock_publish_cloudevent,
                           test_async_client, mock_db_find_one):
    """
    Test Case : Test KernelCI API /user/register endpoint to create admin user
    when requested with admin user's bearer token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'email', 'groups', 'is_active'
        'is_verified' and 'is_superuser' keys
    """
    user = UserRead(
        id='61bda8f2eb1a63d2b7152419',
        username='test_admin',
        email='test-admin@kernelci.org',
        groups=[UserGroup(name='admin')],
        is_active=True,
        is_verified=False,
        is_superuser=True
    )
    mock_db_create.return_value = user
    mock_db_find_one.return_value = UserGroup(name='admin')

    response = await test_async_client.post(
        "user/register",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({
            'username': 'test_admin',
            'password': 'test',
            'email': 'test-admin@kernelci.org',
            'is_superuser': True
        })
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser', 'is_verified',
            'username', 'groups') == tuple(response.json().keys())


@pytest.mark.asyncio
async def test_create_user_endpoint_negative(mock_get_current_user,
                                             mock_publish_cloudevent,
                                             test_async_client):
    """
    Test Case : Test KernelCI API /user/register endpoint when requested
    with regular user's bearer token
    Expected Result :
        HTTP Response Code 401 Unauthorized
        JSON with 'detail' key denoting 'Access denied' error
    """
    mock_get_current_user.return_value = None, "Access denied"

    response = await test_async_client.post(
        "user/register",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
        data=json.dumps({
            'username': 'test',
            'password': 'test',
            'email': 'test@kernelci.org'
        })
    )
    print(response.json())
    assert response.status_code == 401
    assert response.json() == {'detail': 'Access denied'}


@pytest.mark.asyncio
async def test_create_user_with_group(  # pylint: disable=too-many-arguments
                           mock_db_create, mock_publish_cloudevent,
                           test_async_client, mock_db_find_one):
    """
    Test Case : Test KernelCI API /user/register endpoint to create a user
    with a user group
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'email', 'groups', 'is_active'
        'is_verified' and 'is_superuser' keys
    """
    user = UserRead(
        id='61bda8f2eb1a63d2b7152419',
        username='test_admin',
        email='test-admin@kernelci.org',
        groups=[UserGroup(name='kernelci')],
        is_active=True,
        is_verified=False,
        is_superuser=False
    )
    mock_db_create.return_value = user
    mock_db_find_one.return_value = UserGroup(name='kernelci')

    response = await test_async_client.post(
        "user/register",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({
            'username': 'test',
            'password': 'test',
            'email': 'test-admin@kernelci.org',
            'groups': ['kernelci']
        })
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser', 'is_verified',
            'username', 'groups') == tuple(response.json().keys())


@pytest.mark.asyncio
async def test_get_user_by_id_endpoint(mock_db_find_by_id,
                                       test_async_client):
    """
    Test Case : Test KernelCI API GET /user/{user_id} endpoint with admin
    token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with User object attributes
    """
    user_obj = UserRead(
            id='61bda8f2eb1a63d2b7152418',
            username='test',
            email='test@kernelci.org',
            groups=[],
            is_active=True,
            is_verified=False,
            is_superuser=False
        )
    mock_db_find_by_id.return_value = user_obj

    response = await test_async_client.get(
        "user/61bda8f2eb1a63d2b7152418",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        })
    print("response.json()", response.json())
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser', 'is_verified',
            'username', 'groups') == tuple(response.json().keys())
