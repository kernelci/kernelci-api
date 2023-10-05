# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# Disable flag as user models don't require any public methods
# at the moment
# pylint: disable=too-few-public-methods

"""User model definitions"""

from typing import Optional
from pydantic import conlist, Field
from fastapi_users.db import BeanieBaseUser
from fastapi_users import schemas
from beanie import (
    Indexed,
    Document,
    PydanticObjectId,
)
from .models import DatabaseModel, UserGroup, ModelId


class User(BeanieBaseUser, Document,  # pylint: disable=too-many-ancestors
           DatabaseModel):
    """API User model"""
    username: Indexed(str, unique=True)
    groups: conlist(UserGroup, unique_items=True) = Field(
        default=[],
        description="A list of groups that user belongs to"
    )

    class Settings(BeanieBaseUser.Settings):
        """Configurations"""
        # MongoDB collection name for model
        name = "user"


class UserRead(schemas.BaseUser[PydanticObjectId], ModelId):
    """Schema for reading a user"""
    username: Indexed(str, unique=True)
    groups: conlist(UserGroup, unique_items=True)


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a user"""
    username: Indexed(str, unique=True)
    groups: Optional[conlist(str, unique_items=True)]


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating a user"""
    username: Optional[Indexed(str, unique=True)]
    groups: Optional[conlist(str, unique_items=True)]
