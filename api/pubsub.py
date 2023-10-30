# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""Pub/Sub implementation"""

import asyncio

import aioredis
from cloudevents.http import CloudEvent, to_json
from pydantic import BaseModel, Field
from .config import PubSubSettings


class Subscription(BaseModel):
    """Pub/Sub subscription object model"""
    id: int = Field(
        description='Subscription ID'
    )
    channel: str = Field(
        description='Subscription channel name'
    )


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
        # self._settings = Settings()
        self._settings = PubSubSettings()
        if host is None:
            host = self._settings.redis_host
        if db_number is None:
            db_number = self._settings.redis_db_number
        self._redis = aioredis.from_url(f'redis://{host}/{db_number}')
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
            for channel in sub.channels.keys():
                self._channels.add(channel.decode())

    async def subscribe(self, channel):
        """Subscribe to a Pub/Sub channel

        Subscribe to a given channel and return a Subscription object
        containing the subscription id which can then be used again in other
        methods.
        """
        sub_id = await self._redis.incr(self.ID_KEY)
        async with self._lock:
            sub = self._redis.pubsub()
            self._subscriptions[sub_id] = sub
            await sub.subscribe(channel)
            self._update_channels()
            self._start_keep_alive_timer()
            return Subscription(id=sub_id, channel=channel)

    async def unsubscribe(self, sub_id):
        """Unsubscribe from a Pub/Sub channel

        Unsubscribe from a channel using the provided subscription id as found
        in a Subscription object.
        """
        async with self._lock:
            sub = self._subscriptions[sub_id]
            self._subscriptions.pop(sub_id)
            self._update_channels()
            await sub.unsubscribe()

    async def listen(self, sub_id):
        """Listen for Pub/Sub messages

        Listen on a given subscription id asynchronously and return a message
        when received.  Messages about subscribing to the channel are silenced.
        """
        async with self._lock:
            sub = self._subscriptions[sub_id]

        while True:
            msg = await sub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if msg is not None:
                return msg

    async def publish(self, channel, message):
        """Publish a message on a channel

        Publish an arbitrary message asynchronously on a Pub/Sub channel.
        """
        await self._redis.publish(channel, message)

    async def publish_cloudevent(self, channel, data, attributes=None):
        """Publish a CloudEvent on a Pub/Sub channel

        Publish a CloudEvent asynchronously on a given channel using the
        provided data and optional attributes.  The data is the payload of the
        message.  The attributes are the type and source of event which will be
        populated by default if not provided.  See the CloudEvent documentation
        for more details.
        """
        if not attributes:
            attributes = {
                "type": "api.kernelci.org",
                "source": self._settings.cloud_events_source,
            }
        event = CloudEvent(attributes=attributes, data=data)
        await self.publish(channel, to_json(event))
