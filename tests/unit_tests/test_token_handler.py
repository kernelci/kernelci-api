# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>
#
# Copyright (C) 2022, 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API token handler"""

import pytest
from api.models import UserGroup
from api.user_models import User


@pytest.mark.asyncio
async def test_token_endpoint(mock_db_find_one_by_attributes,
                              test_async_client):
    """
    Test Case : Test KernelCI API /user/login endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'access_token' and 'token_type' key
    """
    user = User(
        username='bob',
        password='hello',
        email='bob@kernelci.org',
        groups=[]
    )
    mock_db_find_one_by_attributes.return_value = user
    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data="username=bob&password=hello"
    )
    assert response.status_code == 200
    assert ('access_token', 'token_type') == tuple(response.json().keys())


@pytest.mark.asyncio
async def test_token_endpoint_incorrect_password(mock_db_find_one_by_attributes,
                                                 test_async_client):
    """
    Test Case : Test KernelCI API /user/login endpoint for negative path
    Incorrect password should be passed to the endpoint

    Expected Result :
        HTTP Response Code 401 Unauthorized
        JSON with 'detail' key
    """
    user = User(
        username='bob',
        password='hello',
        email='bob@kernelci.org',
        groups=[]
    )
    mock_db_find_one_by_attributes.return_value = user

    # Pass incorrect password
    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data="username=bob&password=hello"
    )
    print("response json", response.json())
    assert response.status_code == 401
    assert response.json() == {'detail': 'Incorrect username or password'}


@pytest.mark.asyncio
async def test_token_endpoint_admin_user(mock_db_find_one_by_attributes,
                                         test_async_client):
    """
    Test Case : Test KernelCI API /user/login endpoint for admin user
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'access_token' and 'token_type' key
    """
    user = User(
        username='test_admin',
        password='hello',
        email='test-admin@kernelci.org',
        groups=[UserGroup(name='admin')])
    mock_db_find_one_by_attributes.return_value = user
    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data="username=test_admin&password=hello"
    )
    print("json", response.json())
    assert response.status_code == 200
    assert ('access_token', 'token_type') == tuple(response.json().keys())
