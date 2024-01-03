# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Paweł Wieczorek <pawel.wieczorek@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""End-to-end test functions for KernelCI API password reset handler"""

import json
import pytest


@pytest.mark.dependency(
    depends=["e2e_tests/test_user_creation.py::test_create_regular_user"],
    scope="session",
)
@pytest.mark.order("last")
@pytest.mark.asyncio
async def test_password_endpoint(test_async_client):
    """
    Test Case : Test KernelCI API /user/me endpoint to set a new password
    when requested with current user's access token
    Expected Result :
        HTTP Response Code 200 OK
    """
    response = await test_async_client.patch(
        "user/me",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
        },
        data=json.dumps(
            {
                "password": "foo"
            }
        ),
    )
    assert response.status_code == 200
