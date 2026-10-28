# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Module settings"""

from pydantic import EmailStr
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Authentication settings"""

    secret_key: str
    unified_secret: str = ""
    algorithm: str = "HS256"
    # Set to None so tokens don't expire
    access_token_expire_seconds: float = 315360000
    invite_token_expire_seconds: int = 60 * 60 * 24 * 7  # 7 days
    public_base_url: str | None = None


class PubSubSettings(BaseSettings):
    """Pub/Sub settings loaded from the environment"""

    cloud_events_source: str = "https://api.kernelci.org/"
    redis_host: str = "redis"
    redis_db_number: int = 1
    # Every pub/sub subscription pins one dedicated Redis connection, so the
    # pool must be large enough for all concurrent subscribers plus regular
    # commands.  redis-py >= 8 defaults to only 100.
    redis_max_connections: int = 1000
    # Maximum number of concurrent subscriptions a single user may hold.
    # Before the limit is enforced, that user's subscriptions which were
    # never polled and are older than abandoned_subscription_seconds are
    # evicted, so a crash-looping client cannot pile them up.
    max_subscriptions_per_user: int = 20
    abandoned_subscription_seconds: int = 60
    keep_alive_period: int = 45
    # MongoDB durable pub/sub settings
    event_ttl_days: int = 7  # Auto-delete events after N days
    max_catchup_events: int = 1000  # Max events to deliver on reconnect
    subscriber_state_ttl_days: int = 30  # Cleanup unused subscriber states


class EmailSettings(BaseSettings):
    """Email settings"""

    smtp_host: str
    smtp_port: int
    email_sender: EmailStr
    email_password: str
