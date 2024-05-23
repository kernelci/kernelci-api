# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""Pub/Sub implementation"""

import asyncio

import json
from datetime import datetime
from redis import asyncio as aioredis
from cloudevents.http import CloudEvent, to_json
from .models import Subscription, SubscriptionStats
from .config import PubSubSettings


class PubSub:
    """Pub/Sub implementation class

    This class provides a Pub/Sub implementation based on Redis.  The `host`
    and `db_number` parameters can be specified to connect to a particular
    Redis database.  By default, the `redis` host will be used as it is
    available from the `docker-compose` setup.
    """

    ID_KEY = 'kernelci-api-pubsub-id'

    @classmethod
    async def create(cls, *args, **kwargs):
        """Create and return a PubSub object asynchronously"""
        pubsub = PubSub(*args, **kwargs)
        await pubsub._init_sub_id()
        return pubsub

    def __init__(self, host=None, db_number=None):
        self._settings = PubSubSettings()
        if host is None:
            host = self._settings.redis_host
        if db_number is None:
            db_number = self._settings.redis_db_number
        self._redis = aioredis.from_url(f'redis://{host}/{db_number}')
        # self._subscriptions is a dict that matches a subscription id
        # (key) with a Subscription object ('sub') and a redis
        # PubSub object ('redis_sub'). For instance:
        # {1 : {'sub': <Subscription>, 'redis_sub': <PubSub>}}
        #
        # Note that this matching is kept in this dict only.
        self._subscriptions = {}
        self._channels = set()
        self._lock = asyncio.Lock()
        self._keep_alive_timer = None

    async def _init_sub_id(self):
        await self._redis.setnx(self.ID_KEY, 0)

    def _start_keep_alive_timer(self):
        if not self._settings.keep_alive_period:
            return
        if not self._keep_alive_timer or self._keep_alive_timer.done():
            loop = asyncio.get_running_loop()
            self._keep_alive_timer = asyncio.run_coroutine_threadsafe(
                self._keep_alive(), loop)

    async def _keep_alive(self):
        while True:
            async with self._lock:
                channels = self._channels.copy()
            if not channels:
                break
            for channel in channels:
                await self.publish_cloudevent(channel, "BEEP")
            await asyncio.sleep(self._settings.keep_alive_period)

    def _update_channels(self):
        self._channels = set()
        for sub in self._subscriptions.values():
            for channel in sub['redis_sub'].channels.keys():
                self._channels.add(channel.decode())

    async def subscribe(self, channel, user, options=None):
        """Subscribe to a Pub/Sub channel

        Subscribe to a given channel and return a Subscription object.
        """
        sub_id = await self._redis.incr(self.ID_KEY)
        async with self._lock:
            redis_sub = self._redis.pubsub()
            sub = Subscription(id=sub_id, channel=channel, user=user)
            if options and options.get('promiscuous'):
                sub.promiscuous = True
            await redis_sub.subscribe(channel)
            self._subscriptions[sub_id] = {'redis_sub': redis_sub,
                                           'sub': sub,
                                           'created': datetime.utcnow(),
                                           'last_poll': None}
            self._update_channels()
            self._start_keep_alive_timer()
            return sub

    async def unsubscribe(self, sub_id, user=None):
        """Unsubscribe from a Pub/Sub channel

        Unsubscribe from a channel using the provided subscription id as found
        in a Subscription object.
        """
        async with self._lock:
            sub = self._subscriptions[sub_id]
            # Only allow a user to unsubscribe its own
            # subscriptions. One exception: let an anonymous (internal)
            # call to this function to unsubscribe any subscription
            if user and user != sub['sub'].user:
                raise RuntimeError(f"Subscription {sub_id} "
                                   f"not owned by {user}")
            self._subscriptions.pop(sub_id)
            self._update_channels()
            await sub['redis_sub'].unsubscribe()
            # shut down pubsub connection
            await sub['redis_sub'].close()

    async def listen(self, sub_id, user=None):
        """Listen for Pub/Sub messages

        Listen on a given subscription id asynchronously and return a message
        when received.  Messages about subscribing to the channel are silenced.
        """
        async with self._lock:
            sub = self._subscriptions[sub_id]

        # Only allow a user to listen to its own subscriptions. One
        # exception: let an anonymous (internal) call to this function
        # to listen to any subscription
        if user and user != sub['sub'].user:
            raise RuntimeError(f"Subscription {sub_id} "
                               f"not owned by {user}")
        while True:
            self._subscriptions[sub_id]['last_poll'] = datetime.utcnow()
            msg = await sub['redis_sub'].get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if msg is None:
                continue
            msg_data = json.loads(msg['data'])
            # If the subscription is promiscuous, return the message
            # without checking the owner
            if sub['sub'].promiscuous:
                return msg
            # If the subscription is not promiscuous, check the owner of the
            # message
            if 'owner' in msg_data and msg_data['owner'] != sub['sub'].user:
                continue
            return msg

    async def publish(self, channel, message):
        """Publish a message on a channel

        Publish an arbitrary message asynchronously on a Pub/Sub channel.
        """
        await self._redis.publish(channel, message)

    async def push(self, list_name, message):
        """Push a message onto the tail of a list

        Push an arbitrary message asynchronously on a List.
        """
        await self._redis.rpush(list_name, message)

    async def pop(self, list_name):
        """Pop a message from a list

        Listen on a given list asynchronously and get a message
        when received. Only a single consumer will receive the message.
        """
        while True:
            msg = await self._redis.blpop(list_name, timeout=1.0)
            data = json.loads(msg[1].decode('utf-8')) if msg else None
            if data is not None:
                return data

    async def publish_cloudevent(self, channel, data, attributes=None):
        """Publish a CloudEvent on a Pub/Sub channel

        Publish a CloudEvent asynchronously on a given channel using the
        provided data and optional attributes.  The data is the payload of the
        message.  The attributes are the type and source of event which will be
        populated by default if not provided.  See the CloudEvent documentation
        for more details.
        """
        if not attributes:
            attributes = {}
        if not attributes.get('type'):
            attributes['type'] = "api.kernelci.org"
        if not attributes.get('source'):
            attributes['source'] = self._settings.cloud_events_source
        event = CloudEvent(attributes=attributes, data=data)
        await self.publish(channel, to_json(event))

    async def push_cloudevent(self, list_name, data, attributes=None):
        """Push a CloudEvent on a list

        Push a CloudEvent asynchronously on a given list using the
        provided data and optional attributes.  The data is the payload of the
        message.  The attributes are the type and source of event which will be
        populated by default if not provided.
        """
        if not attributes:
            attributes = {
                "type": "api.kernelci.org",
                "source": self._settings.cloud_events_source,
            }
        event = CloudEvent(attributes=attributes, data=data)
        await self.push(list_name, to_json(event))

    async def subscription_stats(self):
        """Get existing subscription details"""
        subscriptions = []
        for _, subscription in self._subscriptions.items():
            sub = subscription['sub']
            stats = SubscriptionStats(
                id=sub.id,
                channel=sub.channel,
                user=sub.user,
                created=subscription['created'],
                last_poll=subscription['last_poll']
            )
            subscriptions.append(stats)
        return subscriptions
