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
from api.models import UserRead


@pytest.mark.asyncio
async def test_whoami_endpoint(test_async_client, mock_auth_current_user):
    """
    Test Case : Test KernelCI API /whoami endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'hashed_password'
        and 'active' keys
    """
    user = UserRead(
            id='61bda8f2eb1a63d2b7152420',
            username='test-user',
            email='test-user@kernelci.org',
            groups=[],
            is_active=True,
            is_verified=False,
            is_superuser=False
        )
    mock_auth_current_user.return_value = user, BEARER_TOKEN
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
            'is_verified', 'username',
            'groups') == tuple(response.json().keys())
