# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

import aioredis
import asyncio
from cloudevents.http import CloudEvent, to_json
from pydantic import BaseModel, BaseSettings


class Settings(BaseSettings):
    cloud_events_source: str = "https://api.kernelci.org/"
    redis_host: str = "redis"
    redis_db_number: int = 1


class Subscription(BaseModel):
    id: int
    channel: str


class PubSub:
    ID_KEY = 'kernelci-api-pubsub-id'

    @classmethod
    async def create(self, *args, **kwargs):
        pubsub = PubSub(*args, **kwargs)
        await pubsub._init_sub_id()
        return pubsub

    def __init__(self, host=None, db=None):
        self._settings = Settings()
        if host is None:
            host = self._settings.redis_host
        if db is None:
            db = self._settings.redis_db_number
        self._redis = aioredis.from_url(f'redis://{host}/{db}')
        self._subscriptions = dict()
        self._lock = asyncio.Lock()

    async def _init_sub_id(self):
        await self._redis.setnx(self.ID_KEY, 0)

    async def subscribe(self, channel):
        sub_id = await self._redis.incr(self.ID_KEY)
        async with self._lock:
            sub = self._redis.pubsub()
            self._subscriptions[sub_id] = sub
            await sub.subscribe(channel)
            return Subscription(id=sub_id, channel=channel)

    async def unsubscribe(self, sub_id):
        async with self._lock:
            sub = self._subscriptions.get(sub_id)
            if sub:
                self._subscriptions.pop(sub_id)
                await sub.unsubscribe()
                return True
            return False

    async def listen(self, sub_id):
        async with self._lock:
            sub = self._subscriptions.get(sub_id)
            if not sub:
                return None

        while True:
            msg = await sub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if msg is not None:
                return msg

    async def publish(self, channel, message):
        await self._redis.publish(channel, message)

    async def publish_cloudevent(self, channel, data, attributes=None):
        """
        CloudEvent contructor needs to have below params:
            attributes : dict with type and source keys
            data : dict with message key
        """
        if attributes is None:
            attributes = {
                "type": "api.kernelci.org",
                "source": self._settings.cloud_events_source,
            }
        event = CloudEvent(attributes=attributes, data=data)
        await self.publish(channel, to_json(event))
