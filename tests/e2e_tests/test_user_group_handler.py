# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""End-to-end test functions for KernelCI API user group handler"""

import pytest
from cloudevents.http import from_json
import json

from api.models import UserGroup
from api.db import Database
from e2e_tests.conftest import db_create
from .listen_handler import create_listen_task


@pytest.mark.dependency()
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_create_user_groups():
    """
    Test Case : Create default user groups
    """
    default_user_groups = ['admin']
    for group in default_user_groups:
        obj = await db_create(
            Database.COLLECTIONS[UserGroup],
            UserGroup(name=group))
        assert obj is not None


@pytest.mark.dependency(
    depends=["test_create_user_groups"])
@pytest.mark.asyncio
async def test_get_user_group(test_async_client):
    """
    Test Case : Get user groups
    Expected Result :
        HTTP Response Code 200 OK
        Returns dictionary with UserGroup objects, total number of groups
        returned along with limit and offset values
    """
    response = await test_async_client.get(
        "groups",
    )
    assert response.status_code == 200
    assert response.json().keys() == {
            'items',
            'total',
            'limit',
            'offset',
        }
    assert response.json()['total'] == 1
    assert response.json()['items'][0]['name'] == 'admin'


@pytest.mark.dependency(
    depends=[
        'e2e_tests/test_subscribe_handler.py::test_subscribe_user_group_channel'],
    scope='session')
@pytest.mark.asyncio
async def test_create_and_get_user_group(test_async_client):
    """
    Test Case : Create and get a user group by ID

    At first, the test will create asyncio 'Task' instance to receive
    pubsub events from 'user_group' channel.
    A user group with name 'kernelci' will be created using POST '/group'
    request. The 'created' event will be received from the listener task.
    The GET '/group/{group_id}' will be sent using group id from event data
    to get newly created user group object.
    """
    
    # Create Task to listen pubsub event on 'user_group' channel
    task_listen = create_listen_task(test_async_client,
                                     pytest.user_group_channel_subscription_id)
    
    # Create a user group
    response = await test_async_client.post(
        "group",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.ADMIN_BEARER_TOKEN}"
        },
        data=json.dumps({"name": "kernelci"})
    )
    assert response.status_code == 200
    assert response.json().keys() == {
        'id',
        'name',
    }

    # Get result from the event
    await task_listen
    event_data = from_json(task_listen.result().json().get('data')).data
    assert {'op', 'id'} == event_data.keys()

    # Get user group by ID
    response = await test_async_client.get(
        f"group/{event_data['id']}"
    )
    assert response.status_code == 200
    assert response.json()['name'] == 'kernelci'
