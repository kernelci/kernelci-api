# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2023 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""User authentication utilities"""

from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, BaseSettings, Field
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from .db import Database
from .models import User


class Token(BaseModel):
    """Authentication token model"""
    access_token: str = Field(
        description='Authentication access token'
    )
    token_type: str = Field(
        description='Access token type e.g. Bearer'
    )


class Settings(BaseSettings):
    """Authentication settings"""
    secret_key: str
    algorithm: str = "HS256"
    # Set to None so tokens don't expire
    access_token_expire_minutes: float = None


class Authentication:
    """Authentication utility class

    This class accepts a single argument `database` in its constructor, which
    should be a db.Database object.
    """

    CRYPT_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def __init__(self, database: Database, token_url: str, user_scopes: dict):
        self._db = database
        self._settings = Settings()
        self._user_scopes = user_scopes
        self._oauth2_scheme = OAuth2PasswordBearer(
                tokenUrl=token_url,
                scopes=self._user_scopes
        )

    @property
    def oauth2_scheme(self):
        """Get authentication scheme"""
        return self._oauth2_scheme

    @classmethod
    def get_password_hash(cls, password):
        """Get a password hash for a given clear text password string"""
        return cls.CRYPT_CTX.hash(password)

    @classmethod
    def verify_password(cls, password_hash, user):
        """Verify that the password hash matches the user's password"""
        return cls.CRYPT_CTX.verify(password_hash, user.hashed_password)

    async def authenticate_user(self, username: str, password: str):
        """Authenticate a username / password pair

        Look up a `User` in the database with the provided `username`
        and check whether the provided clear text `password` matches the hash
        associated with it.
        """
        user = await self._db.find_one_by_attributes(
            User, {'profile.username': username})
        if not user:
            return False
        if not self.verify_password(password, user.profile):
            return False
        return user.profile

    def create_access_token(self, data: dict):
        """Create a JWT access token using the provided arbitrary `data`"""
        to_encode = data.copy()
        if self._settings.access_token_expire_minutes:
            expires_delta = timedelta(
                    minutes=self._settings.access_token_expire_minutes
                    )
            expire = datetime.utcnow() + expires_delta
            to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self._settings.secret_key, algorithm=self._settings.algorithm
            )
        return encoded_jwt

    async def get_current_user(self, token, security_scopes):
        """Decode the given JWT `token` and look up a matching `User`"""
        try:
            payload = jwt.decode(
                token,
                self._settings.secret_key,
                algorithms=[self._settings.algorithm]
            )
            username: str = payload.get("sub")
            token_scopes = payload.get("scopes", [])
            if username is None:
                return None, "Could not validate credentials"

            for scope in security_scopes:
                if scope not in token_scopes:
                    return None, "Access denied"

        except JWTError as error:
            return None, str(error)

        user = await self._db.find_one_by_attributes(
            User, {'profile.username': username})
        return user, None

    async def validate_scopes(self, requested_scopes):
        """Check if requested scopes are valid user scopes"""
        for scope in requested_scopes:
            if scope not in self._user_scopes:
                return False, scope
        return True, None

    def get_jwt_strategy(self) -> JWTStrategy:
        """Get JWT strategy for authentication backend"""
        return JWTStrategy(
            secret=self._settings.secret_key,
            lifetime_seconds=self._settings.access_token_expire_minutes
        )

    def get_user_authentication_backend(self):
        """Authentication backend for user management

        Authentication backend for `fastapi-users` is composed of two
        parts: Transaport and Strategy.
        Transport is a mechanism for token transmisson i.e. bearer or cookie.
        Strategy is a method to generate and secure tokens. It can be JWT,
        database or Redis.
        """
        bearer_transport = BearerTransport(tokenUrl="user/login")
        return AuthenticationBackend(
            name="jwt",
            transport=bearer_transport,
            get_strategy=self.get_jwt_strategy,
        )
