# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""User authentication utilities"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, BaseSettings, Field
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


class TokenData(BaseModel):
    """Authentication token associated data model"""
    username: Optional[str] = Field(
        default=None,
        description='Username associated with the provided token'
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

    def __init__(self, database: Database):
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._db = database
        self._settings = Settings()

    def get_password_hash(self, password):
        """Get a password hash for a given clear text password string"""
        return self._pwd_context.hash(password)

    async def authenticate_user(self, username: str, password: str):
        """Authenticate a username / password pair

        Look up a `User` in the database with the provided `username` and check
        whether the provided clear text `password` matches the hash associated
        with it.
        """
        user = await self._db.find_one(User, username=username)
        if not user:
            return False
        if not self._pwd_context.verify(password, user.hashed_password):
            return False
        return user

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

    async def get_current_user(self, token):
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
                return None, None
            token_data = TokenData(username=username)
        except JWTError:
            return None, None

        return await self._db.find_one(
            User, username=token_data.username), token_scopes
