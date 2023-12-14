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
from kernelci.api.models_base import DatabaseModel, ModelId


class UserGroup(DatabaseModel):
    """API model to group associated user accounts"""
    name: str = Field(
        description="User group name"
    )

    @classmethod
    def create_indexes(cls, collection):
        """Create an index to bind unique constraint to group name"""
        collection.create_index("name", unique=True)


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

    @classmethod
    def create_indexes(cls, collection):
        """Create an index to bind unique constraint to email"""
        collection.create_index("email", unique=True)


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
