# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2025 Collabora Limited

"""Unit test functions for KernelCI API user group handler"""

import json

from api.models import PageModel, UserGroup
from tests.unit_tests.conftest import ADMIN_BEARER_TOKEN


def test_list_user_groups(mock_db_find_by_attributes, test_client):
    """GET /user-groups returns a paginated list of user groups."""
    group_1 = {"id": "65265305c74695807499037f", "name": "team-a"}
    group_2 = {"id": "65265305c746958074990370", "name": "team-b"}
    mock_db_find_by_attributes.return_value = PageModel(
        items=[group_1, group_2],
        total=2,
        limit=50,
        offset=0,
    )

    response = test_client.get(
        "user-groups",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN,
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_create_user_group(mock_db_find_one, mock_db_create, test_client):
    """POST /user-groups creates a new user group."""
    mock_db_find_one.return_value = None
    mock_db_create.return_value = UserGroup(name="runtime:pull-labs-demo:node-editor")

    response = test_client.post(
        "user-groups",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN,
        },
        data=json.dumps({"name": "runtime:pull-labs-demo:node-editor"}),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "runtime:pull-labs-demo:node-editor"


def test_delete_user_group(mock_db_find_by_id, mock_db_count,
                           mock_db_delete_by_id, test_client):
    """DELETE /user-groups/{id} removes an unused user group."""
    mock_db_find_by_id.return_value = UserGroup(name="team-a")
    mock_db_count.return_value = 0

    response = test_client.delete(
        "user-groups/65265305c74695807499037f",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN,
        },
    )
    assert response.status_code == 204
    mock_db_delete_by_id.assert_called_once_with(
        UserGroup,
        "65265305c74695807499037f",
    )


def test_delete_user_group_when_assigned(mock_db_find_by_id, mock_db_count,
                                         test_client):
    """DELETE /user-groups/{id} rejects when group is assigned to users."""
    mock_db_find_by_id.return_value = UserGroup(name="team-a")
    mock_db_count.return_value = 2

    response = test_client.delete(
        "user-groups/65265305c74695807499037f",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"].startswith("User group is assigned")
