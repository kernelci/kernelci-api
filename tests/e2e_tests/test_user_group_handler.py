# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""End-to-end test functions for KernelCI API user group handler"""

import json
import pytest
from cloudevents.http import from_json

from .listen_handler import create_listen_task


@pytest.mark.dependency(
    depends=[
        'tests/e2e_tests/test_subscribe_handler.py::test_subscribe_user_group_channel'],
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
                                     pytest.user_group_channel_subscription_id)  # pylint: disable=no-member

    # Create a user group
    response = await test_async_client.post(
        "group",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.ADMIN_BEARER_TOKEN}"  # pylint: disable=no-member
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
