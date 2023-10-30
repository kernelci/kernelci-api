# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2023 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""User authentication utilities"""

from passlib.context import CryptContext
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from .config import AuthSettings


class Authentication:
    """Authentication utility class"""

    CRYPT_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def __init__(self, token_url: str):
        self._settings = AuthSettings()
        self._token_url = token_url

    @classmethod
    def get_password_hash(cls, password):
        """Get a password hash for a given clear text password string"""
        return cls.CRYPT_CTX.hash(password)

    def get_jwt_strategy(self) -> JWTStrategy:
        """Get JWT strategy for authentication backend"""
        return JWTStrategy(
            secret=self._settings.secret_key,
            algorithm=self._settings.algorithm,
            lifetime_seconds=self._settings.access_token_expire_seconds
        )

    def get_user_authentication_backend(self):
        """Authentication backend for user management

        Authentication backend for `fastapi-users` is composed of two
        parts: Transaport and Strategy.
        Transport is a mechanism for token transmisson i.e. bearer or cookie.
        Strategy is a method to generate and secure tokens. It can be JWT,
        database or Redis.
        """
        bearer_transport = BearerTransport(tokenUrl=self._token_url)
        return AuthenticationBackend(
            name="jwt",
            transport=bearer_transport,
            get_strategy=self.get_jwt_strategy,
        )
