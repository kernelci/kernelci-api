# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2026 Collabora Limited
# Author: Denys Fedoryshchenko <denys.f@collabora.com>

"""Unit tests for the MongoDB-backed Pub/Sub Redis connection handling"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
from redis import exceptions as redis_exceptions

from api.pubsub_mongo import PubSub, SubscriptionLimitError


@pytest.fixture
def mongo_pubsub(mocker):
    """PubSub instance backed by fakeredis and a dummy Mongo client"""
    pubsub = PubSub(mongo_client=MagicMock())
    mocker.patch.object(pubsub, "_redis", fakeredis.aioredis.FakeRedis())
    # Keep-alive timer is irrelevant here and needs a running loop thread
    mocker.patch.object(pubsub, "_start_keep_alive_timer")
    return pubsub


@pytest.mark.asyncio
async def test_cleanup_never_polled_subscription(mongo_pubsub):
    """
    Test Case: A subscription that was created but never polled must be
    removed once it is older than the stale cutoff.

    Expected Result:
        cleanup_stale_subscriptions() returns 1 and the subscription is
        gone from PubSub._subscriptions, releasing its Redis connection.
    """
    sub = await mongo_pubsub.subscribe("node", "test")
    assert mongo_pubsub._subscriptions[sub.id]["last_poll"] is None
    mongo_pubsub._subscriptions[sub.id]["created"] = (
        datetime.utcnow() - timedelta(minutes=20)
    )

    cleaned = await mongo_pubsub.cleanup_stale_subscriptions(15)

    assert cleaned == 1
    assert not mongo_pubsub._subscriptions


@pytest.mark.asyncio
async def test_cleanup_keeps_fresh_subscriptions(mongo_pubsub):
    """
    Test Case: Subscriptions that are either recently created or recently
    polled must survive the stale cleanup.

    Expected Result:
        cleanup_stale_subscriptions() returns 0 and both entries remain.
    """
    fresh = await mongo_pubsub.subscribe("node", "test")
    polled = await mongo_pubsub.subscribe("node", "test")
    mongo_pubsub._subscriptions[polled.id]["created"] = (
        datetime.utcnow() - timedelta(hours=5)
    )
    mongo_pubsub._subscriptions[polled.id]["last_poll"] = datetime.utcnow()

    cleaned = await mongo_pubsub.cleanup_stale_subscriptions(15)

    assert cleaned == 0
    assert set(mongo_pubsub._subscriptions) == {fresh.id, polled.id}


@pytest.mark.asyncio
async def test_rebuild_closes_old_redis_subscription(mongo_pubsub):
    """
    Test Case: Rebuilding the Redis subscription after a connection error
    must close the previous PubSub object.

    Expected Result:
        The old PubSub is unsubscribed and closed, and the subscription
        entry points at a new PubSub object.
    """
    sub = await mongo_pubsub.subscribe("node", "test")
    sub_data = mongo_pubsub._subscriptions[sub.id]
    old_redis_sub = AsyncMock()
    sub_data["redis_sub"] = old_redis_sub

    await mongo_pubsub._rebuild_redis_subscription(sub.id, sub, sub_data)

    old_redis_sub.unsubscribe.assert_awaited_once()
    old_redis_sub.aclose.assert_awaited_once()
    assert sub_data["redis_sub"] is not old_redis_sub
    assert (
        mongo_pubsub._subscriptions[sub.id]["redis_sub"]
        is sub_data["redis_sub"]
    )


@pytest.mark.asyncio
async def test_subscribe_failure_releases_connection(mongo_pubsub, mocker):
    """
    Test Case: When the Redis SUBSCRIBE command fails, the half-initialised
    PubSub must be closed and nothing recorded in PubSub._subscriptions.

    Expected Result:
        The Redis error propagates, the PubSub object is closed and no
        subscription entry is left behind.
    """
    failing_sub = AsyncMock()
    failing_sub.subscribe.side_effect = redis_exceptions.MaxConnectionsError(
        "Too many connections"
    )
    mocker.patch.object(
        mongo_pubsub._redis, "pubsub", MagicMock(return_value=failing_sub)
    )

    with pytest.raises(redis_exceptions.MaxConnectionsError):
        await mongo_pubsub.subscribe("node", "test")

    failing_sub.aclose.assert_awaited_once()
    assert not mongo_pubsub._subscriptions


@pytest.mark.asyncio
async def test_keep_alive_survives_redis_error(mongo_pubsub, mocker):
    """
    Test Case: A Redis error while publishing the keep-alive BEEP must not
    terminate the keep-alive loop.

    Expected Result:
        _keep_alive() keeps iterating after the failed publish and only
        stops once there are no channels left to keep alive.
    """
    await mongo_pubsub.subscribe("node", "test")
    publish = mocker.patch.object(
        mongo_pubsub,
        "_publish_keepalive",
        AsyncMock(side_effect=redis_exceptions.MaxConnectionsError("Too many")),
    )

    async def drop_channels(_period):
        # Simulate the last subscriber going away during the sleep
        mongo_pubsub._channels = set()

    mocker.patch("api.pubsub_mongo.asyncio.sleep", side_effect=drop_channels)

    await mongo_pubsub._keep_alive()

    publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_limit_per_user(mongo_pubsub):
    """
    Test Case: A user may hold at most max_subscriptions_per_user active
    subscriptions; another user is not affected by that count.

    Expected Result:
        The 21st subscribe() for the same user raises
        SubscriptionLimitError while a different user can still subscribe.
    """
    limit = mongo_pubsub._settings.max_subscriptions_per_user
    assert limit == 20
    for _ in range(limit):
        sub = await mongo_pubsub.subscribe("node", "greedy")
        # Recently polled subscriptions are legitimately active
        mongo_pubsub._subscriptions[sub.id]["last_poll"] = datetime.utcnow()

    with pytest.raises(SubscriptionLimitError):
        await mongo_pubsub.subscribe("node", "greedy")

    other = await mongo_pubsub.subscribe("node", "other")
    assert other.user == "other"
    assert len(mongo_pubsub._subscriptions) == limit + 1


@pytest.mark.asyncio
async def test_subscribe_evicts_abandoned_subscriptions(mongo_pubsub):
    """
    Test Case: Never-polled subscriptions older than one minute belonging
    to the subscribing user are evicted before the limit is enforced, but
    fresh never-polled ones (client may still be about to listen) are kept.

    Expected Result:
        The old abandoned subscriptions disappear, the fresh one survives,
        and the new subscribe() succeeds despite the user having been at
        the limit.
    """
    limit = mongo_pubsub._settings.max_subscriptions_per_user
    old = datetime.utcnow() - timedelta(minutes=2)
    abandoned_ids = []
    for _ in range(limit - 1):
        sub = await mongo_pubsub.subscribe("node", "crashy")
        mongo_pubsub._subscriptions[sub.id]["created"] = old
        abandoned_ids.append(sub.id)
    fresh = await mongo_pubsub.subscribe("node", "crashy")

    new = await mongo_pubsub.subscribe("node", "crashy")

    remaining = set(mongo_pubsub._subscriptions)
    assert not remaining & set(abandoned_ids)
    assert remaining == {fresh.id, new.id}
