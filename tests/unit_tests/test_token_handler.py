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
from fastapi_users.exceptions import UserNotExists
from api.user_models import User


@pytest.mark.asyncio
async def test_token_endpoint(test_async_client, mock_user_find):
    """
    Test Case : Test KernelCI API /user/login endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'access_token' and 'token_type' key
    """
    user = User(
        id='65265305c74695807499037f',
        username='bob',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4K',
        email='bob@kernelci.org',
        groups=[],
        is_active=True,
        is_superuser=False,
        is_verified=True
    )
    mock_user_find.return_value = user
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
async def test_token_endpoint_incorrect_password(test_async_client,
                                                 mock_user_find):
    """
    Test Case : Test KernelCI API /user/login endpoint for negative path
    Incorrect password should be passed to the endpoint

    Expected Result :
        HTTP Response Code 400 Bad Request
        JSON with 'detail' key
    """
    mock_user_find.side_effect = UserNotExists

    # Pass incorrect password
    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data="username=bob&password=hello1"
    )
    print("response json", response.json())
    assert response.status_code == 400
    assert response.json() == {'detail': 'LOGIN_BAD_CREDENTIALS'}
