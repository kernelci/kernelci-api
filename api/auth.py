# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""User authentication utilities"""

from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, BaseSettings, Field
from .db import Database
from .models import User
from fastapi_users.db import BeanieUserDatabase, ObjectIDIDMixin
from fastapi_users import BaseUserManager
from typing import Optional, Any, Dict
from .models import TestUser
from beanie import PydanticObjectId
from fastapi import Depends, Request, Response


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


SECRET = "SECRET"

class UserManager(ObjectIDIDMixin, BaseUserManager[TestUser, PydanticObjectId]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: TestUser, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_login(
        self,
        user: TestUser,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ):
        print(f"User {user.id} logged in.")

    async def on_after_forgot_password(
        self, user: TestUser, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: TestUser, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")
        return {"token": token}

    async def on_after_verify(
        self, user: TestUser, request: Optional[Request] = None
    ):
        print(f"Verification successful for user {user.id}")

    async def on_after_update(
        self,
        user: TestUser,
        update_dict: Dict[str, Any],
        request: Optional[Request] = None,
    ):
        print(f"User {user.id} has been updated with {update_dict}.")

    async def on_before_delete(self, user: TestUser, request: Optional[Request] = None):
        print(f"User {user.id} is going to be deleted")

async def get_user_db():
        """Database adapter for fastapi-users"""
        yield BeanieUserDatabase(TestUser)

async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)
