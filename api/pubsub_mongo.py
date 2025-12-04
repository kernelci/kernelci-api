# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2025 Collabora Limited
# Author: Denys Fedoryshchenko <denys.f@collabora.com>

# pylint: disable=duplicate-code
# Note: This module intentionally shares interface code with pubsub.py
# as both implement the same PubSub API contract

"""MongoDB-based Pub/Sub implementation with optional durable delivery

This module provides a hybrid Pub/Sub implementation:
- Without subscriber_id: Traditional fire-and-forget (events lost if
  not listening)
- With subscriber_id: Durable delivery with catch-up on missed events

Events are stored in MongoDB with TTL for automatic cleanup.
"""

import logging
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from redis import asyncio as aioredis
from cloudevents.http import CloudEvent, to_json
from pymongo import ASCENDING, WriteConcern
from motor import motor_asyncio

from .models import Subscription, SubscriptionStats, SubscriberState
from .config import PubSubSettings

logger = logging.getLogger(__name__)


class PubSub:  # pylint: disable=too-many-instance-attributes
    """Hybrid Pub/Sub implementation with MongoDB durability

    Supports two modes:
    1. Fire-and-forget (no subscriber_id): Uses Redis pub/sub, events lost if
       subscriber not listening
    2. Durable (with subscriber_id): Events stored in MongoDB, subscriber can
       catch up on missed events after reconnection

    The subscriber_id should be unique per subscriber instance (e.g.,
    "scheduler-prod-1", "dashboard-main"). Multiple subscribers with the same
    username can use different subscriber_ids to track their positions
    independently.
    """

    ID_KEY = 'kernelci-api-pubsub-id'
    EVENT_SEQ_KEY = 'kernelci-api-event-seq'

    # Collection names
    # Use existing eventhistory collection for unified event storage
    EVENT_HISTORY_COLLECTION = 'eventhistory'
    SUBSCRIBER_STATE_COLLECTION = 'subscriber_state'

    # Default settings
    DEFAULT_MAX_CATCHUP_EVENTS = 1000

    @classmethod
    async def create(cls, *args, mongo_client=None, **kwargs):
        """Create and return a PubSub object asynchronously"""
        pubsub = cls(*args, mongo_client=mongo_client, **kwargs)
        await pubsub._init()
        return pubsub

    def __init__(self, mongo_client=None, host=None, db_number=None,
                 mongo_db_name='kernelci'):
        self._settings = PubSubSettings()
        if host is None:
            host = self._settings.redis_host
        if db_number is None:
            db_number = self._settings.redis_db_number

        self._redis = aioredis.from_url(
            f'redis://{host}/{db_number}', health_check_interval=30
        )

        # MongoDB setup
        if mongo_client is None:
            mongo_service = os.getenv('MONGO_SERVICE') or 'mongodb://db:27017'
            self._mongo_client = motor_asyncio.AsyncIOMotorClient(
                mongo_service)
        else:
            self._mongo_client = mongo_client
        self._mongo_db = self._mongo_client[mongo_db_name]

        # In-memory subscription tracking (for fire-and-forget mode)
        # {sub_id: {'sub': Subscription, 'redis_sub': PubSub,
        #           'subscriber_id': str|None, ...}}
        self._subscriptions: Dict[int, Dict[str, Any]] = {}
        self._channels = set()
        self._lock = asyncio.Lock()
        self._keep_alive_timer = None

    async def _init(self):
        """Initialize Redis and MongoDB resources"""
        await self._redis.setnx(self.ID_KEY, 0)
        await self._redis.setnx(self.EVENT_SEQ_KEY, 0)
        await self._migrate_eventhistory_if_needed()
        await self._ensure_indexes()

    async def _migrate_eventhistory_if_needed(self):
        """Detect old eventhistory format and migrate if needed

        Old format (24h TTL, no sequence_id):
        - timestamp index with expireAfterSeconds: 86400

        New format (7 days TTL, with sequence_id):
        - timestamp index with expireAfterSeconds: 604800
        - compound index on (channel, sequence_id)
        """
        col = self._mongo_db[self.EVENT_HISTORY_COLLECTION]

        # Check if collection exists
        collections = await self._mongo_db.list_collection_names()
        if self.EVENT_HISTORY_COLLECTION not in collections:
            logger.info(
                "eventhistory collection does not exist, will be created")
            return

        # Check existing indexes
        indexes = await col.index_information()

        # Look for old TTL index (24h = 86400 seconds)
        old_format_detected = False
        has_sequence_index = False

        for _, index_info in indexes.items():
            # Check for old 24h TTL
            if 'expireAfterSeconds' in index_info:
                ttl = index_info['expireAfterSeconds']
                if ttl == 86400:
                    old_format_detected = True
                    logger.warning(
                        "Detected old eventhistory format (24h TTL). "
                        "Migration required."
                    )

            # Check for new sequence_id index
            if 'key' in index_info:
                keys = [k[0] for k in index_info['key']]
                if 'sequence_id' in keys:
                    has_sequence_index = True

        if old_format_detected and not has_sequence_index:
            await self._migrate_eventhistory(col)

    async def _migrate_eventhistory(self, col):
        """Migrate eventhistory collection to new format

        Strategy: Drop old indexes and collection data, recreate fresh.
        Old data has 24h TTL anyway, so max 24h of history is lost.
        """
        logger.warning("Migrating eventhistory collection to new format...")

        try:
            # Drop all indexes except _id
            indexes = await col.index_information()
            for index_name in indexes:
                if index_name != '_id_':
                    logger.info("Dropping index: %s", index_name)
                    await col.drop_index(index_name)

            # Drop all documents (they lack required fields)
            result = await col.delete_many({})
            logger.info(
                "Deleted %d old eventhistory documents",
                result.deleted_count
            )

            logger.info("eventhistory migration complete")

        except Exception as exc:
            logger.error("eventhistory migration failed: %s", exc)
            raise

    async def _ensure_indexes(self):
        """Create MongoDB indexes for eventhistory and subscriber_state

        Creates indexes required for durable pub/sub functionality.
        """
        event_col = self._mongo_db[self.EVENT_HISTORY_COLLECTION]
        sub_col = self._mongo_db[self.SUBSCRIBER_STATE_COLLECTION]

        # Event history indexes
        # TTL index for auto-cleanup (7 days = 604800 seconds)
        # Note: If index already exists with different TTL, this is a no-op.
        # Migration handles dropping the old index first.
        await event_col.create_index(
            'timestamp',
            expireAfterSeconds=604800,
            name='ttl_timestamp'
        )
        # Compound index for efficient pub/sub catch-up queries
        await event_col.create_index(
            [('channel', ASCENDING), ('sequence_id', ASCENDING)],
            name='channel_sequence_id'
        )

        # Subscriber state indexes
        # Unique index on subscriber_id
        await sub_col.create_index(
            'subscriber_id',
            unique=True,
            name='unique_subscriber_id'
        )
        # Index for stale cleanup
        await sub_col.create_index(
            'last_poll',
            name='last_poll'
        )

    def _start_keep_alive_timer(self):
        """Start keep-alive timer for Redis pub/sub connections"""
        if not self._settings.keep_alive_period:
            return
        if not self._keep_alive_timer or self._keep_alive_timer.done():
            loop = asyncio.get_running_loop()
            self._keep_alive_timer = asyncio.run_coroutine_threadsafe(
                self._keep_alive(), loop)

    async def _keep_alive(self):
        """Send periodic BEEP to keep connections alive"""
        while True:
            async with self._lock:
                channels = self._channels.copy()
            if not channels:
                break
            for channel in channels:
                # Use _publish_keepalive to avoid storing BEEP in MongoDB
                await self._publish_keepalive(channel, "BEEP")
            await asyncio.sleep(self._settings.keep_alive_period)

    async def _publish_keepalive(self, channel: str, data: str):
        """Publish keep-alive message (Redis only, no MongoDB storage)"""
        attributes = {
            'type': "api.kernelci.org",
            'source': self._settings.cloud_events_source,
        }
        event = CloudEvent(attributes=attributes, data=data)
        await self._redis.publish(channel, to_json(event))

    def _update_channels(self):
        """Update tracked channels from active subscriptions"""
        self._channels = set()
        for sub in self._subscriptions.values():
            if sub.get('redis_sub'):
                for channel in sub['redis_sub'].channels.keys():
                    self._channels.add(channel.decode())

    async def _get_next_event_id(self) -> int:
        """Get next sequential event ID from Redis"""
        return await self._redis.incr(self.EVENT_SEQ_KEY)

    async def _store_event(self, channel: str, data: Dict[str, Any],
                           owner: Optional[str] = None) -> int:
        """Store event in eventhistory collection and return sequence ID

        Uses the same collection as /events API endpoint (EventHistory model).
        The data dict is stored directly in the 'data' field.
        """
        sequence_id = await self._get_next_event_id()
        event_doc = {
            'timestamp': datetime.utcnow(),
            'sequence_id': sequence_id,
            'channel': channel,
            'owner': owner,
            'data': data,
        }
        col = self._mongo_db[self.EVENT_HISTORY_COLLECTION]
        # Use w=1 for acknowledged writes (durability)
        await col.with_options(
            write_concern=WriteConcern(w=1)
        ).insert_one(event_doc)
        return sequence_id

    async def _get_subscriber_state(
            self, subscriber_id: str) -> Optional[Dict]:
        """Get subscriber state from MongoDB"""
        col = self._mongo_db[self.SUBSCRIBER_STATE_COLLECTION]
        return await col.find_one({'subscriber_id': subscriber_id})

    async def _update_subscriber_state(self, subscriber_id: str,
                                       last_event_id: int,
                                       last_poll: datetime = None):
        """Update subscriber's last_event_id and last_poll"""
        col = self._mongo_db[self.SUBSCRIBER_STATE_COLLECTION]
        update = {'last_event_id': last_event_id}
        if last_poll:
            update['last_poll'] = last_poll
        await col.update_one(
            {'subscriber_id': subscriber_id},
            {'$set': update}
        )

    def _eventhistory_to_cloudevent(self, event: Dict) -> str:
        """Convert eventhistory document to CloudEvent JSON string

        Reconstructs CloudEvent format from stored eventhistory data
        for consistent delivery format between catch-up and real-time events.
        """
        attributes = {
            'type': 'api.kernelci.org',
            'source': self._settings.cloud_events_source,
        }
        if event.get('owner'):
            attributes['owner'] = event['owner']

        ce = CloudEvent(attributes=attributes, data=event.get('data', {}))
        return to_json(ce).decode('utf-8')

    # pylint: disable=too-many-arguments
    async def _get_missed_events(self, channel: str, after_seq_id: int,
                                 owner_filter: Optional[str] = None,
                                 promiscuous: bool = False,
                                 limit: int = None) -> List[Dict]:
        """Get events after a given sequence ID for catch-up

        Queries the eventhistory collection used by /events API.
        Returns events sorted by sequence_id for ordered delivery.
        """
        if limit is None:
            limit = self.DEFAULT_MAX_CATCHUP_EVENTS

        col = self._mongo_db[self.EVENT_HISTORY_COLLECTION]
        query = {
            'channel': channel,
            'sequence_id': {'$gt': after_seq_id}
        }

        # If not promiscuous, filter by owner
        if not promiscuous and owner_filter:
            query['$or'] = [
                {'owner': owner_filter},
                {'owner': None},
                {'owner': {'$exists': False}}
            ]

        cursor = col.find(query).sort('sequence_id', ASCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def subscribe(self, channel: str, user: str,
                        options: Optional[Dict] = None) -> Subscription:
        """Subscribe to a Pub/Sub channel

        Args:
            channel: Channel name to subscribe to
            user: Username of subscriber
            options: Optional dict with:
                - promiscuous: bool - receive all messages regardless of owner
                - subscriber_id: str - enable durable delivery with this ID

        Returns:
            Subscription object with id, channel, user, promiscuous fields
        """
        sub_id = await self._redis.incr(self.ID_KEY)
        subscriber_id = options.get('subscriber_id') if options else None
        promiscuous = options.get('promiscuous', False) if options else False

        async with self._lock:
            redis_sub = self._redis.pubsub()
            sub = Subscription(
                id=sub_id,
                channel=channel,
                user=user,
                promiscuous=promiscuous
            )
            await redis_sub.subscribe(channel)

            self._subscriptions[sub_id] = {
                'redis_sub': redis_sub,
                'sub': sub,
                'subscriber_id': subscriber_id,
                'created': datetime.utcnow(),
                'last_poll': None,
                'pending_catchup': [],  # Events to deliver before real-time
                'catchup_done': not subscriber_id,
            }
            self._update_channels()
            self._start_keep_alive_timer()

        # If subscriber_id provided, set up durable subscription
        if subscriber_id:
            await self._setup_durable_subscription(
                sub_id, subscriber_id, channel, user, promiscuous
            )

        return sub

    # pylint: disable=too-many-arguments
    async def _setup_durable_subscription(
            self, sub_id: int, subscriber_id: str,
            channel: str, user: str, promiscuous: bool):
        """Set up or restore durable subscription state"""
        col = self._mongo_db[self.SUBSCRIBER_STATE_COLLECTION]
        existing = await col.find_one({'subscriber_id': subscriber_id})

        if existing:
            # Existing subscriber - verify ownership
            if existing['user'] != user:
                raise RuntimeError(
                    f"Subscriber {subscriber_id} owned by different user"
                )
            # Load pending catch-up events
            missed = await self._get_missed_events(
                channel=existing['channel'],
                after_seq_id=existing['last_event_id'],
                owner_filter=user,
                promiscuous=promiscuous
            )
            async with self._lock:
                self._subscriptions[sub_id]['pending_catchup'] = missed
                sub = self._subscriptions[sub_id]
                sub['last_acked_id'] = existing['last_event_id']
            logger.info(
                "Subscriber %s reconnected, %d missed events",
                subscriber_id, len(missed)
            )
        else:
            # New subscriber - get current event ID as starting point
            current_id = int(await self._redis.get(self.EVENT_SEQ_KEY) or 0)
            state = SubscriberState(
                subscriber_id=subscriber_id,
                channel=channel,
                user=user,
                promiscuous=promiscuous,
                last_event_id=current_id,
                created_at=datetime.utcnow()
            )
            await col.insert_one(state.model_dump())
            async with self._lock:
                self._subscriptions[sub_id]['last_acked_id'] = current_id
            logger.info(
                "New durable subscriber %s starting at event %d",
                subscriber_id, current_id
            )

    async def unsubscribe(self, sub_id: int, user: Optional[str] = None):
        """Unsubscribe from a Pub/Sub channel

        Note: For durable subscriptions, the subscriber state is preserved
        in MongoDB to allow reconnection and catch-up.
        """
        async with self._lock:
            sub = self._subscriptions.get(sub_id)
            if not sub:
                raise KeyError(f"Subscription {sub_id} not found")

            # Only allow user to unsubscribe their own subscriptions
            if user and user != sub['sub'].user:
                raise RuntimeError(
                    f"Subscription {sub_id} not owned by {user}"
                )

            self._subscriptions.pop(sub_id)
            self._update_channels()
            await sub['redis_sub'].unsubscribe()
            await sub['redis_sub'].close()

    async def listen(self, sub_id: int,
                     user: Optional[str] = None) -> Optional[Dict]:
        # pylint: disable=too-many-branches
        """Listen for Pub/Sub messages

        For durable subscriptions (with subscriber_id):
        1. First delivers any missed events from catch-up queue
        2. Then waits for real-time events
        3. Implicitly ACKs previous event when called again

        Returns message dict or None on error.
        """
        async with self._lock:
            sub_data = self._subscriptions.get(sub_id)
            if not sub_data:
                raise KeyError(f"Subscription {sub_id} not found")

        sub = sub_data['sub']
        subscriber_id = sub_data.get('subscriber_id')

        # Ownership check
        if user and user != sub.user:
            raise RuntimeError(f"Subscription {sub_id} not owned by {user}")

        # For durable subscriptions, handle implicit ACK
        if subscriber_id and sub_data.get('last_delivered_id'):
            await self._update_subscriber_state(
                subscriber_id,
                sub_data['last_delivered_id'],
                datetime.utcnow()
            )
            sub_data['last_acked_id'] = sub_data['last_delivered_id']

        # Check for pending catch-up events first
        if sub_data.get('pending_catchup'):
            event = sub_data['pending_catchup'].pop(0)
            sub_data['last_delivered_id'] = event['sequence_id']
            self._subscriptions[sub_id]['last_poll'] = datetime.utcnow()
            # Reconstruct CloudEvent format from eventhistory data
            cloudevent_data = self._eventhistory_to_cloudevent(event)
            return {
                'channel': sub.channel,
                'data': cloudevent_data,
                'pattern': None,
                'type': 'message'
            }

        # Mark catch-up as complete
        if not sub_data.get('catchup_done'):
            sub_data['catchup_done'] = True

        # Real-time listening via Redis
        while True:
            self._subscriptions[sub_id]['last_poll'] = datetime.utcnow()
            msg = None
            try:
                msg = await sub_data['redis_sub'].get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
            except aioredis.ConnectionError:
                async with self._lock:
                    channel = sub.channel
                    new_redis_sub = self._redis.pubsub()
                    await new_redis_sub.subscribe(channel)
                    self._subscriptions[sub_id]['redis_sub'] = new_redis_sub
                    sub_data['redis_sub'] = new_redis_sub
                continue
            except aioredis.RedisError as exc:
                logger.error("Redis error: %s", exc)
                return None

            if msg is None:
                continue

            msg_data = json.loads(msg['data'])

            # For durable subscriptions, track the sequence ID
            if subscriber_id and isinstance(msg_data, dict):
                sequence_id = msg_data.get('_sequence_id')
                if sequence_id:
                    sub_data['last_delivered_id'] = sequence_id

            # Filter by owner if not promiscuous
            if sub.promiscuous:
                return msg
            if 'owner' in msg_data and msg_data['owner'] != sub.user:
                continue
            return msg

    async def publish(self, channel: str, message: str):
        """Publish a message on a channel (Redis only, no durability)"""
        await self._redis.publish(channel, message)

    async def publish_cloudevent(self, channel: str, data: Any,
                                 attributes: Optional[Dict] = None):
        """Publish a CloudEvent on a Pub/Sub channel

        Events are:
        1. Stored in MongoDB eventhistory (for durable subscribers and
           /events API)
        2. Published to Redis as CloudEvent (for real-time delivery)

        The data is stored as-is in eventhistory.data field, and wrapped
        in CloudEvent format for Redis delivery.
        """
        if not attributes:
            attributes = {}
        if not attributes.get('type'):
            attributes['type'] = "api.kernelci.org"
        if not attributes.get('source'):
            attributes['source'] = self._settings.cloud_events_source

        owner = attributes.get('owner')

        # Store in MongoDB eventhistory (for durable delivery and /events API)
        # Store the raw data dict, not CloudEvent JSON
        sequence_id = await self._store_event(channel, data, owner)

        # Create CloudEvent for Redis real-time delivery
        event = CloudEvent(attributes=attributes, data=data)
        event_json = to_json(event).decode('utf-8')

        # Add sequence_id to message for tracking durable subscriptions
        msg_with_id = json.loads(event_json)
        msg_with_id['_sequence_id'] = sequence_id
        await self._redis.publish(channel, json.dumps(msg_with_id))

    async def push(self, list_name: str, message: str):
        """Push a message onto the tail of a list"""
        await self._redis.rpush(list_name, message)

    async def pop(self, list_name: str) -> Optional[Dict]:
        """Pop a message from a list"""
        while True:
            msg = await self._redis.blpop(list_name, timeout=1.0)
            data = json.loads(msg[1].decode('utf-8')) if msg else None
            if data is not None:
                return data

    async def push_cloudevent(self, list_name: str, data: Any,
                              attributes: Optional[Dict] = None):
        """Push a CloudEvent on a list"""
        if not attributes:
            attributes = {
                "type": "api.kernelci.org",
                "source": self._settings.cloud_events_source,
            }
        event = CloudEvent(attributes=attributes, data=data)
        await self.push(list_name, to_json(event))

    async def subscription_stats(self) -> List[SubscriptionStats]:
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

    async def cleanup_stale_subscriptions(self,
                                          max_age_minutes: int = 30) -> int:
        """Remove subscriptions not polled recently

        For durable subscriptions, only the in-memory state is cleaned up.
        The MongoDB subscriber state is preserved for reconnection.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        stale_ids = []

        async with self._lock:
            for sub_id, sub_data in self._subscriptions.items():
                last_poll = sub_data.get('last_poll')
                if last_poll and last_poll < cutoff:
                    stale_ids.append(sub_id)

        for sub_id in stale_ids:
            try:
                await self.unsubscribe(sub_id)
            except KeyError:
                pass

        return len(stale_ids)

    async def cleanup_stale_subscriber_states(self,
                                              max_age_days: int = 30) -> int:
        """Remove subscriber states not used for a long time

        This is separate from subscription cleanup - it removes the
        persistent MongoDB state for subscribers that haven't reconnected.
        """
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        col = self._mongo_db[self.SUBSCRIBER_STATE_COLLECTION]
        result = await col.delete_many({'last_poll': {'$lt': cutoff}})
        return result.deleted_count
