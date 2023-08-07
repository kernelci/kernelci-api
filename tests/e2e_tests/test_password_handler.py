# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Paweł Wieczorek <pawel.wieczorek@collabora.com>

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
    Test Case : Test KernelCI API /password endpoint to set a new password
    when requested with current user's password
    Expected Result :
        HTTP Response Code 200 OK
    """
    response = await test_async_client.post(
        "password?username=test_user",
        data=json.dumps(
            {
                "current_password": {"password": "test"},
                "new_password": {"password": "foo"},
            }
        ),
    )
    assert response.status_code == 200
