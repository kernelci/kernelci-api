# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test functions for KernelCI API user group handler"""

import json

from tests.unit_tests.conftest import (
    ADMIN_BEARER_TOKEN,
    BEARER_TOKEN,
)
from api.models import UserGroup


def test_create_user_group(mock_init_sub_id, mock_get_current_admin_user,
                           mock_db_create, mock_publish_cloudevent,
                           test_client):
    """
    Test Case : Test KernelCI API /group endpoint to create user group
    when requested with admin user's bearer token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id' and 'name' keys
    """
    mock_db_create.return_value = UserGroup(
        id='61bda8f2eb1a63d2b7152422',
        name='kernelci')

    response = test_client.post(
        "group",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({"name": "kernelci"})
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'name') == tuple(response.json().keys())


def test_create_group_endpoint_negative(mock_init_sub_id,
                                        mock_get_current_user,
                                        mock_publish_cloudevent,
                                        test_client):
    """
    Test Case : Test KernelCI API /group endpoint when requested
    with regular user's bearer token
    Expected Result :
        HTTP Response Code 401 Unauthorized
        JSON with 'detail' key denoting 'Access denied' error
    """
    mock_get_current_user.return_value = None, "Access denied"

    response = test_client.post(
        "group",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
        data=json.dumps({"name": "kernelci"})
    )
    print(response.json())
    assert response.status_code == 401
    assert response.json() == {'detail': 'Access denied'}
