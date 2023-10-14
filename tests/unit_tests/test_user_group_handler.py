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
from api.paginator_models import PageModel


def test_create_user_group(mock_db_create, mock_publish_cloudevent,
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


def test_create_group_endpoint_negative(mock_publish_cloudevent,
                                        test_client):
    """
    Test Case : Test KernelCI API /group endpoint when requested
    with regular user's bearer token
    Expected Result :
        HTTP Response Code 403 Forbidden
        JSON with 'detail' key denoting 'Forbidden' error
    """
    response = test_client.post(
        "group",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
        data=json.dumps({"name": "kernelci"})
    )
    print(response.json())
    assert response.status_code == 403
    assert response.json() == {'detail': 'Forbidden'}


def test_get_groups(mock_db_find_by_attributes,
                    test_client):
    """
    Test Case : Test KernelCI API GET /groups endpoint
    Expected Result :
        HTTP Response Code 200 OK
        List of all the user group objects
    """
    user_group_1 = {
        "id": "61bda8f2eb1a63d2b7152421",
        "name": "admin"}
    user_group_2 = {
        "id": "61bda8f2eb1a63d2b7152422",
        "name": "kernelci"}
    mock_db_find_by_attributes.return_value = PageModel(
        items=[user_group_1, user_group_2],
        total=2,
        limit=50,
        offset=0
    )
    response = test_client.get("groups")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert ('items', 'total', 'limit',
            'offset') == tuple(response.json().keys())


def test_get_group_by_id(mock_db_find_by_id,
                         test_client):
    """
    Test Case : Test KernelCI API GET /group/{group_id} endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with UserGroup object
    """
    mock_db_find_by_id.return_value = UserGroup(id='61bda8f2eb1a63d2b7152422',
                                                name='kernelci')

    response = test_client.get("group/61bda8f2eb1a63d2b7152422")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().keys() == {'id', 'name'}
