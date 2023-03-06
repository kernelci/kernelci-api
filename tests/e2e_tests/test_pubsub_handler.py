# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test function for KernelCI API pubsub handler"""

import pytest
from cloudevents.http import CloudEvent, to_structured, from_json

from .listen_handler import create_listen_task


@pytest.mark.asyncio
async def test_pubsub_handler(test_async_client):
    """
    Test KernelCI API Pub/Sub.
    Publish event using '/publish' endpoint on 'test_channel'.
    Use pubsub listener task to verify published event message.
    """
    # Create Task to listen pubsub event on 'test_channel' channel
    task_listen = create_listen_task(test_async_client,
                                     pytest.test_channel_subscription_id)

    # Created and publish CloudEvent
    attributes = {
        "type": "api.kernelci.org",
        "source": "https://api.kernelci.org/",
    }
    data = {"message": "Test message"}
    event = CloudEvent(attributes, data)
    headers, body = to_structured(event)
    headers['Authorization'] = f"Bearer {pytest.BEARER_TOKEN}"
    response = await test_async_client.post(
        "publish/test_channel",
        headers=headers,
        data=body
        )
    assert response.status_code == 200

    # Get result of pubsub event listener
    await task_listen
    assert task_listen.result().json().keys() == {
        'channel',
        'data',
        'pattern',
        'type',
    }
    event_data = from_json(task_listen.result().json().get('data')).data
    assert ('message',) == tuple(event_data.keys())
    assert event_data.get('message') == 'Test message'
