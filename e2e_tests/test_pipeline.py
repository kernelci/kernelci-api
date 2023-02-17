# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""Run test pipeline for KernelCI API"""

import pytest
from cloudevents.http import from_json

from .listen_handler import create_listen_task
from .test_node_handler import create_node, get_node_by_id, update_node


@pytest.mark.dependency(
    depends=[
        'e2e_tests/test_subscribe_handler.py::test_subscribe_node_channel'],
    scope='session')
@pytest.mark.order(4)
@pytest.mark.asyncio
async def test_node_pipeline(test_async_client):
    """
    The function is used to run a test node pipeline.
    Pipeline flow:

    The pipeline will create asyncio 'Task' instance to run it in the
    background to receive pubsub events using '/listen' endpoint.
    A sample 'checkout' node will be created using POST '/node' request.
    The 'created' event will be received from the listener task.
    The GET '/node/{node_id}' will be sent using node id from event data to
    get newly created node object.
    Again, a task for listening to pubsub will be created to receive events
    on node channel.
    The PUT '/node' request will update the node with modified 'node.state'
    field. At the end, the listener task will receive node 'updated' event.
    """

    # Create Task to listen pubsub event on 'node' channel
    task_listen = create_listen_task(test_async_client,
                                     pytest.node_channel_subscription_id)

    # Create a node
    node = {
        "name": "checkout",
        "path": ["checkout"],
        "revision": {
            "tree": "mainline",
            "url": "https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
            "branch": "master",
            "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
            "describe": "v5.16-rc4-31-g2a987e65025e"
        }
    }
    response = await create_node(test_async_client, node)

    # Get result of pubsub event listen task
    await task_listen
    event_data = from_json(task_listen.result().json().get('data')).data
    assert ('op', 'id') == tuple(event_data.keys())
    assert event_data.get('op') == 'created'
    assert event_data.get('id') == response.json()['_id']

    # Get node id from event data and get created node by id
    response = await get_node_by_id(test_async_client, event_data.get('id'))
    node = response.json()

    # Create Task to listen 'updated' event on 'node' channel
    task_listen = create_listen_task(test_async_client,
                                     pytest.node_channel_subscription_id)

    # Update node.state
    node.update({"state": "done"})
    # Update the node
    await update_node(test_async_client, node)

    # Get result of pubsub event listen task
    await task_listen
    event_data = from_json(task_listen.result().json().get('data')).data
    assert ('op', 'id') == tuple(event_data.keys())
    assert event_data.get('op') == 'updated'
