# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

import aioredis
import asyncio


class PubSub:

    def __init__(self, host='redis', db=1):
        self._redis = aioredis.from_url(f'redis://{host}/{db}')
        self._subscriptions = dict()
        self._lock = asyncio.Lock()

    async def subscribe(self, user, channel):
        async with self._lock:
            key = (user.id, channel)
            if key not in self._subscriptions:
                sub = self._redis.pubsub()
                self._subscriptions[key] = sub
                await sub.subscribe(channel)
                return True
            return False

    async def unsubscribe(self, user, channel):
        async with self._lock:
            key = (user.id, channel)
            sub = self._subscriptions.get(key)
            if sub:
                self._subscriptions.pop(key)
                sub.unsubscribe(channel)
                return True
            return False

    async def listen(self, user, channel):
        async with self._lock:
            key = (user.id, channel)
            sub = self._subscriptions.get(key)
            if not sub:
                return None

        while True:
            msg = await sub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if msg is not None:
                return msg

    async def publish(self, user, channel, message):
        await self._redis.publish(channel, message)
