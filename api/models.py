# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# Disable flag as user models don't require any public methods
# at the moment
# pylint: disable=too-few-public-methods

# pylint: disable=no-name-in-module

"""Server-side model definitions"""

from datetime import datetime
from typing import Optional, TypeVar
from pydantic import (
    BaseModel,
    conlist,
    Field,
)
from fastapi import Query
from fastapi_pagination import LimitOffsetPage, LimitOffsetParams
from fastapi_users.db import BeanieBaseUser
from fastapi_users import schemas
from beanie import (
    Indexed,
    Document,
    PydanticObjectId,
)
from bson import ObjectId
from kernelci.api.models_base import DatabaseModel, ModelId


# PubSub model definitions

class Subscription(BaseModel):
    """Pub/Sub subscription object model"""
    id: int = Field(
        description='Subscription ID'
    )
    channel: str = Field(
        description='Subscription channel name'
    )
    user: str = Field(
        description=("Username of the user that created the "
                     "subscription (owner)")
    )


class SubscriptionStats(Subscription):
    """Pub/Sub subscription statistics object model"""
    created: datetime = Field(
        description='Timestamp of connection creation'
    )
    last_poll: Optional[datetime] = Field(
        description='Timestamp when connection last polled for data'
    )


# User model definitions

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


# Pagination models

class CustomLimitOffsetParams(LimitOffsetParams):
    """Model to set custom constraint on limit

    The model is required to redefine limit parameter to remove the number
    validation on maximum value"""

    limit: int = Query(50, ge=1, description="Page size limit")


class PageModel(LimitOffsetPage[TypeVar("T")]):
    """Model for pagination

    This model is required to serialize paginated model data response"""

    __params_type__ = CustomLimitOffsetParams

    class Config:
        """Configuration attributes for PageNode"""
        json_encoders = {
            ObjectId: str,
        }
