# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Michal Galka <michal.galka@collabora.com>

from api.pubsub import PubSub
import fakeredis.aioredis
import pytest


@pytest.fixture()
def mock_pubsub(mocker):
    pubsub = PubSub()
    redis_mock = fakeredis.aioredis.FakeRedis()
    mocker.patch.object(pubsub, '_redis', redis_mock)
    return pubsub


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
    r = await mock_pubsub.subscribe('CHANNEL')
    assert r.channel == 'CHANNEL'
    assert r.id == 1
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
    channels = ((1, 'CHANNEL1'), (2, 'CHANNEL2'), (3, 'CHANNEL3'))
    for expected_id, expected_channel in channels:
        r = await mock_pubsub.subscribe(expected_channel)
        assert r.channel == expected_channel
        assert r.id == expected_id
    assert len(mock_pubsub._subscriptions) == 3
    assert (1, 2, 3) == tuple(mock_pubsub._subscriptions.keys())


@pytest.fixture()
def mock_pubsub_subscriptions(mocker):
    pubsub = PubSub()
    redis_mock = fakeredis.aioredis.FakeRedis()
    mocker.patch.object(pubsub, '_redis', redis_mock)
    subscriptions_mock = dict({1: pubsub._redis.pubsub()})
    mocker.patch.object(pubsub, '_subscriptions', subscriptions_mock)
    return pubsub


@pytest.mark.asyncio
async def test_unsubscribe_sub_id_exists(mock_pubsub_subscriptions):
    """
    Test Case: Unsubscribe with a PubSub.unsubscribe() method when
    subscription ID exists in subscriptions dictionary.

    Expected Result:
        PubSub._subscriptions dict should be empty.
        Return value should be True.
    """
    # In case of subscription id exists
    result = await mock_pubsub_subscriptions.unsubscribe(sub_id=1)
    assert len(mock_pubsub_subscriptions._subscriptions) == 0
    assert result is True


@pytest.mark.asyncio
async def test_unsubscribe_sub_id_not_exists(mock_pubsub_subscriptions):
    """
    Test Case: Unsubscribe with a PubSub.unsubscribe() method when
    subscription ID does not exist in subscriptions dictionary.

    Expected Result:
        PubSub._subscriptions dict should have one entry. This entry's
        key should be equal 1.
        Return value should be False.
    """
    # In case of subscription id does not exist
    result = await mock_pubsub_subscriptions.unsubscribe(sub_id=2)
    assert len(mock_pubsub_subscriptions._subscriptions) == 1
    assert 1 in mock_pubsub_subscriptions._subscriptions
    assert result is False
