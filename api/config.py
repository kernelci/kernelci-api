# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Module settings"""

from pydantic import BaseSettings, EmailStr


class AuthSettings(BaseSettings):
    """Authentication settings"""
    secret_key: str
    algorithm: str = "HS256"
    # Set to None so tokens don't expire
    access_token_expire_seconds: float = None


class PubSubSettings(BaseSettings):
    """Pub/Sub settings loaded from the environment"""
    cloud_events_source: str = "https://api.kernelci.org/"
    redis_host: str = "redis"
    redis_db_number: int = 1
    keep_alive_period: int = 45


class EmailSettings(BaseSettings):
    """Email settings"""
    smtp_host: str
    smtp_port: int
    email_sender: EmailStr
    email_password: str
