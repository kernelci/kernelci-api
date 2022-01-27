# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Michal Galka <michal.galka@collabora.com>

# pylint: disable=protected-access

"""Unit test functions for KernelCI API Pub/Sub"""

import pytest


@pytest.mark.asyncio
async def test_subscribe_single_channel(mock_pubsub):
    """
    Test Case: Subscribe for one channel with a PubSub.subscribe() method.

    Expected Result:
        Subscription-like object is returned from PubSub.subscribe() method
        with channel set to 'CHANNEL', id set to 1, and filters set to None.
        PubSub._subscriptions and PubSub._filters dict should have one entry.
        This entry's key should be equal 1.
    """
    result = await mock_pubsub.subscribe('CHANNEL')
    assert result.channel == 'CHANNEL'
    assert result.id == 1
    assert result.filters is None
    assert len(mock_pubsub._subscriptions) == 1
    assert 1 in mock_pubsub._subscriptions
    assert len(mock_pubsub._filters) == 1
    assert 1 in mock_pubsub._filters


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
        PubSub._subscriptions and PubSub._filters dict should have 3 entries.
        This entries' keys should be 1, 2, and 3.
    """
    channels = ((1, 'CHANNEL1'), (2, 'CHANNEL2'), (3, 'CHANNEL3'))
    for expected_id, expected_channel in channels:
        result = await mock_pubsub.subscribe(expected_channel)
        assert result.channel == expected_channel
        assert result.id == expected_id
        assert result.filters is None
    assert len(mock_pubsub._subscriptions) == 3
    assert len(mock_pubsub._filters) == 3
    assert (1, 2, 3) == tuple(mock_pubsub._subscriptions.keys())
    assert (1, 2, 3) == tuple(mock_pubsub._filters.keys())


@pytest.mark.asyncio
async def test_unsubscribe_sub_id_exists(mock_pubsub_subscriptions):
    """
    Test Case: Unsubscribe with a PubSub.unsubscribe() method when
    subscription ID exists in subscriptions dictionary.

    Expected Result:
        PubSub._subscriptions and PubSub._filters dict should be empty.
    """
    # In case of subscription id exists
    await mock_pubsub_subscriptions.unsubscribe(sub_id=1)
    assert len(mock_pubsub_subscriptions._subscriptions) == 0
    assert len(mock_pubsub_subscriptions._filters) == 0


@pytest.mark.asyncio
async def test_unsubscribe_sub_id_not_exists(mock_pubsub_subscriptions):
    """
    Test Case: Unsubscribe with a PubSub.unsubscribe() method when
    subscription ID does not exist in subscriptions dictionary.

    Expected Result:
        PubSub._subscriptions and PubSub._filters dict should have one entry.
        These entry's key should be equal 1.
    """
    # In case of subscription id does not exist
    with pytest.raises(ValueError):
        await mock_pubsub_subscriptions.unsubscribe(sub_id=2)
    assert len(mock_pubsub_subscriptions._subscriptions) == 1
    assert 1 in mock_pubsub_subscriptions._subscriptions
    assert len(mock_pubsub_subscriptions._filters) == 1
    assert 1 in mock_pubsub_subscriptions._filters
