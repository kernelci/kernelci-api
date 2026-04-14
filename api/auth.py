# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2023 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""User authentication utilities"""

from typing import Optional

import jwt as pyjwt

from fastapi_users import exceptions, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.jwt import SecretType, decode_jwt
from fastapi_users.manager import BaseUserManager
from passlib.context import CryptContext

from .config import AuthSettings


class DualSecretJWTStrategy(JWTStrategy):
    """JWTStrategy that accepts tokens signed with either of two secrets.

    Tokens are always *written* with the primary secret.  On *read*, the
    primary secret is tried first; if verification fails **and** a unified
    secret is configured, the token is retried with the unified secret.
    """

    def __init__(
        self,
        secret: SecretType,
        lifetime_seconds: Optional[int],
        algorithm: str = "HS256",
        unified_secret: str = "",
    ):
        super().__init__(
            secret=secret,
            lifetime_seconds=lifetime_seconds,
            algorithm=algorithm,
        )
        self.unified_secret = unified_secret

    async def read_token(
        self,
        token: Optional[str],
        user_manager: BaseUserManager[models.UP, models.ID],
    ) -> Optional[models.UP]:
        if token is None:
            return None

        # Try primary secret first
        user = await self._decode_and_lookup(
            token, self.decode_key, user_manager
        )
        if user is not None:
            return user

        # Fallback to unified secret
        if self.unified_secret:
            return await self._decode_and_lookup(
                token, self.unified_secret, user_manager
            )

        return None

    async def _decode_and_lookup(
        self,
        token: str,
        secret: SecretType,
        user_manager: BaseUserManager[models.UP, models.ID],
    ) -> Optional[models.UP]:
        try:
            data = decode_jwt(
                token,
                secret,
                self.token_audience,
                algorithms=[self.algorithm],
            )
            user_id = data.get("sub")
            if user_id is None:
                return None
        except pyjwt.PyJWTError:
            return None

        try:
            parsed_id = user_manager.parse_id(user_id)
            return await user_manager.get(parsed_id)
        except (exceptions.UserNotExists, exceptions.InvalidID):
            return None


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

    def get_jwt_strategy(self) -> DualSecretJWTStrategy:
        """Get JWT strategy for authentication backend"""
        return DualSecretJWTStrategy(
            secret=self._settings.secret_key,
            algorithm=self._settings.algorithm,
            lifetime_seconds=self._settings.access_token_expire_seconds,
            unified_secret=self._settings.unified_secret,
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
