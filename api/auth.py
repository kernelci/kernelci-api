# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
import asyncio
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional
from .models import User


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class Authentication:
    # ToDo: use settings https://fastapi.tiangolo.com/advanced/settings/

    # To generate a secret key: openssl rand -hex 32
    SECRET_KEY = \
        "fad13f9cf6e5ff51daac4e6784529daa9d1dc8a80703730221f1090066d929c4"

    ALGORITHM = "HS256"

    # Set to None so tokens don't expire
    ACCESS_TOKEN_EXPIRE_MINUTES = None  # 30

    def __init__(self, db):
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._db = db

    def get_password_hash(self, password):
        return self._pwd_context.hash(password)

    async def authenticate_user(self, username: str, password: str):
        user = await self._db.find_one(User, username=username)
        if not user:
            return False
        if not self._pwd_context.verify(password, user.hashed_password):
            return False
        return user

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        if self.ACCESS_TOKEN_EXPIRE_MINUTES:
            expires_delta = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
            expire = datetime.utcnow() + expires
            to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt

    async def get_current_user(self, token):
        try:
            payload = jwt.decode(
                token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            token_data = TokenData(username=username)
        except JWTError:
            return None

        return await self._db.find_one(User, username=token_data.username)
