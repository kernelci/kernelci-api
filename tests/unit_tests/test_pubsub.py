# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Alexandra Pereira <alexandra.pereira@collabora.com>

# pylint: disable=protected-access

"""Unit test functions for KernelCI API Pub/Sub"""

import json
import pytest


@pytest.mark.asyncio
async def test_subscribe_single_channel(mock_pubsub):
    """
    Test Case: Subscribe for one channel with a PubSub.subscribe() method.

    Expected Result:
        Subscription-like object is returned from PubSub.subscribe() method
        with channel set to 'CHANNEL' and id set to 1.
        PubSub._subscriptions dict should have one entry. This entry's
        key should be equal 1.
    """
    result = await mock_pubsub.subscribe('CHANNEL', 'test')
    assert result.channel == 'CHANNEL'
    assert result.id == 1
    assert len(mock_pubsub._subscriptions) == 1
    assert 1 in mock_pubsub._subscriptions


@pytest.mark.asyncio
async def test_subscribe_multiple_channels(mock_pubsub):
    """
    Test Case: Subscribe for three channels with subsequent calls of
    PubSub.subscribe() method.

    Expected Result:
        Subscription-like objects are returned for each call of
        PubSub.subscribe() method
        Subsequent calls should have channel names: 'CHANNEL1', 'CHANNEL2',
        'CHANNEL3' and should have ids 1, 2, 3 respectively.
        PubSub._subscriptions dict should have 2 entries. This entries'
        keys should be 1, 2, and 3.
    """
    # Reset `ID_KEY` value to get subscription ID starting from 1
    await mock_pubsub._redis.set(mock_pubsub.ID_KEY, 0)
    channels = ((1, 'CHANNEL1'), (2, 'CHANNEL2'), (3, 'CHANNEL3'))
    for expected_id, expected_channel in channels:
        result = await mock_pubsub.subscribe(expected_channel, 'test')
        assert result.channel == expected_channel
        assert result.id == expected_id
    assert len(mock_pubsub._subscriptions) == 3
    assert (1, 2, 3) == tuple(mock_pubsub._subscriptions.keys())


@pytest.mark.asyncio
async def test_unsubscribe_sub_id_exists(mock_pubsub_subscriptions):
    """
    Test Case: Unsubscribe with a PubSub.unsubscribe() method when
    subscription ID exists in subscriptions dictionary.

    Expected Result:
        PubSub._subscriptions dict should be empty.
    """
    # In case of subscription id exists
    await mock_pubsub_subscriptions.unsubscribe(sub_id=1)
    assert len(mock_pubsub_subscriptions._subscriptions) == 0


@pytest.mark.asyncio
async def test_unsubscribe_sub_id_not_exists(mock_pubsub_subscriptions):
    """
    Test Case: Unsubscribe with a PubSub.unsubscribe() method when
    subscription ID does not exist in subscriptions dictionary.

    Expected Result:
        PubSub._subscriptions dict should have one entry. This entry's
        key should be equal 1.
    """
    # In case of subscription id does not exist
    with pytest.raises(KeyError):
        await mock_pubsub_subscriptions.unsubscribe(sub_id=2)
    assert len(mock_pubsub_subscriptions._subscriptions) == 1
    assert 1 in mock_pubsub_subscriptions._subscriptions


@pytest.mark.asyncio
async def test_pubsub_publish_couldevent(mock_pubsub_publish):
    """
    Test Case: Validate and check the json built by the cloud event
    published in the channel by the redis publisher.

    Expected Results:
        Validate that a json is sent to the channel and assert the json values from
        data and attributes parameters in Pubsub.publish_cloudevent(). There's no
        return value, but a json to be published in a channel.
    """

    data = 'validate json'
    attributes = { "specversion": "1.0",  "id": "6878b661-96dc-4e93-8c92-26eb9ff8db64",
    "source": "https://api.kernelci.org/", "type": "api.kernelci.org",
    "time": "2022-01-31T21:29:29.675593+00:00"}

    await mock_pubsub_publish.publish_cloudevent('CHANNEL1', data, attributes)

    expected_json = str.encode('{"specversion": "1.0", '\
    '"id": "6878b661-96dc-4e93-8c92-26eb9ff8db64", "source": "https://api.kernelci.org/", '\
    '"type": "api.kernelci.org", "time": "2022-01-31T21:29:29.675593+00:00", '\
    '"data": "validate json"}')

    json_arg = mock_pubsub_publish._redis.execute_command.call_args.args[2]

    json.loads(json_arg)
    assert json_arg == expected_json
