# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2025 Collabora Limited
#
# pylint: disable=unused-argument

"""End-to-end test functions for KernelCI API invite flow"""

import json
import pytest


@pytest.mark.dependency(
    depends=["tests/e2e_tests/test_user_creation.py::test_create_admin_user"],
    scope="session",
)
@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_invite_and_accept_user(test_async_client):
    username = "invited_user"
    password = "test"
    email = "invited@kernelci.org"

    response = await test_async_client.post(
        "user/invite",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {pytest.ADMIN_BEARER_TOKEN}",
        },
        data=json.dumps(
            {
                "username": username,
                "email": email,
                "send_email": False,
                "return_token": True,
            }
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email_sent"] is False
    assert "token" in body and body["token"]

    response = await test_async_client.post(
        "user/accept-invite",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "token": body["token"],
                "password": password,
            }
        ),
    )
    assert response.status_code == 200
    assert response.json()["is_verified"] is True
    assert response.json()["username"] == username

    response = await test_async_client.post(
        "user/login",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=f"username={username}&password={password}",
    )
    assert response.status_code == 200
    assert response.json().keys() == {"access_token", "token_type"}

