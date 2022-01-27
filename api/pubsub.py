# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""Pub/Sub implementation"""

import asyncio
from typing import Optional

import aioredis
from cloudevents.http import CloudEvent, to_json, from_json
from pydantic import BaseModel, BaseSettings


class Settings(BaseSettings):
    """Pub/Sub settings loaded from the environment"""
    cloud_events_source: str = "https://api.kernelci.org/"
    redis_host: str = "redis"
    redis_db_number: int = 1


class Subscription(BaseModel):
    """Pub/Sub subscription object model"""
    id: int
    channel: str
    filters: Optional[dict] = None


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
        self._settings = Settings()
        if host is None:
            host = self._settings.redis_host
        if db_number is None:
            db_number = self._settings.redis_db_number
        self._redis = aioredis.from_url(f'redis://{host}/{db_number}')
        self._subscriptions = {}
        self._lock = asyncio.Lock()
        self._filters = {}

    async def _init_sub_id(self):
        await self._redis.setnx(self.ID_KEY, 0)

    async def subscribe(self, channel, filters=None):
        """Subscribe to a Pub/Sub channel

        Subscribe to a given channel and return a Subscription object
        containing the subscription id which can then be used again in other
        methods.
        """
        sub_id = await self._redis.incr(self.ID_KEY)
        async with self._lock:
            sub = self._redis.pubsub()
            self._subscriptions[sub_id] = sub
            self._filters[sub_id] = filters
            await sub.subscribe(channel)
            return Subscription(id=sub_id, channel=channel, filters=filters)

    async def unsubscribe(self, sub_id):
        """Unsubscribe from a Pub/Sub channel

        Unsubscribe from a channel using the provided subscription id as found
        in a Subscription object.  Raise a ValueError if the id is not a valid
        one.
        """
        async with self._lock:
            sub = self._subscriptions.get(sub_id)
            if sub is None:
                raise ValueError(f"Invalid subscription id: {sub_id}")
            self._subscriptions.pop(sub_id)
            self._filters.pop(sub_id)
            await sub.unsubscribe()

    def pubsub_event_filter(self, sub_id, msg):
        """Filter Pub/Sub events

        Filter received Pub/Sub event using provided dictionary.
        Return True if the event matches with the filter, otherwise False.
        """
        event_filter_status = True
        filters = self._filters.get(sub_id)
        if not filters:
            return event_filter_status
        msg_data = from_json(msg['data']).data
        for key, value in filters.items():
            if key not in msg_data.keys():
                continue

            if key == 'revision':
                msg_revision_dict = get_revision_dict(msg_data)
                for revision_key, revision_value in value.items():
                    if revision_key not in msg_revision_dict:
                        continue
                    if revision_value != msg_revision_dict[revision_key]:
                        event_filter_status = False
                        break
            elif value != msg_data[key]:
                event_filter_status = False
                break
        return event_filter_status

    async def listen(self, sub_id):
        """Listen for Pub/Sub messages

        Listen on a given subscription id asynchronously and return a message
        when received.  Messages about subscribing to the channel are silenced.
        Raise a ValueError if the id is not a valid one.
        """
        async with self._lock:
            sub = self._subscriptions.get(sub_id)
            if sub is None:
                raise ValueError(f"Invalid subscription id: {sub_id}")

        while True:
            msg = await sub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if msg is not None:
                event_filter_status = self.pubsub_event_filter(sub_id, msg)
                if event_filter_status is False:
                    continue
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
        if attributes is None:
            attributes = {
                "type": "api.kernelci.org",
                "source": self._settings.cloud_events_source,
            }
        event = CloudEvent(attributes=attributes, data=data)
        await self.publish(channel, to_json(event))


def get_revision_dict(msg_data):
    """Get dictionary from revision information of node event"""
    msg_revision_dict = {}
    for item in msg_data['revision'].split(" "):
        item = item.split("=")
        msg_revision_dict[item[0]] = item[1]
    return msg_revision_dict
