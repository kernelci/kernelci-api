# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API whoami handler"""

import pytest
from tests.unit_tests.conftest import BEARER_TOKEN
from api.user_models import User


@pytest.mark.asyncio
async def test_whoami_endpoint(test_async_client, mock_users_router):
    """
    Test Case : Test KernelCI API /whoami endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'hashed_password'
        and 'active' keys
    """
    router = mock_users_router.return_value
    test_user = User(
        username='bob',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4K',
        email='bob@kernelci.org',
        is_active=True,
        is_superuser=False,
        is_verified=True
    )
    @router.get("/whoami", response_model=User)
    async def whoami():
        return test_user

    response = await test_async_client.get(
        "whoami",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
    )
    print(response.json(), response.status_code)
    assert response.status_code == 200
    assert ('id', 'email', 'is_active', 'is_superuser',
            'is_verified', 'username') == tuple(response.json().keys())
