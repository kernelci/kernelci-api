# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API me handler"""

from test.conftest import BEARER_TOKEN

from fastapi.testclient import TestClient

from api.main import app


def test_me_endpoint(mock_get_current_user):
    """
    Test Case : Test KernelCI API /me endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with '_id', 'username', 'hashed_password'
        and 'active' keys
    """
    client = TestClient(app)
    response = client.get(
        "/me",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
    )
    assert response.status_code == 200
    assert ('_id', 'username', 'hashed_password', 'active',
            'is_admin') == tuple(response.json().keys())
