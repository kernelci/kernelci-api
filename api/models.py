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
from typing import Optional, TypeVar, Dict, Any, List
from pydantic import (
    BaseModel,
    Field,
    model_serializer,
    field_validator,
)
from typing_extensions import Annotated
from fastapi import Query
from fastapi_pagination import LimitOffsetPage, LimitOffsetParams
from fastapi_users.db import BeanieBaseUser
from fastapi_users import schemas
from beanie import (
    Indexed,
    Document,
    PydanticObjectId,
)
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
    promiscuous: bool = Field(
        description='Listen to all users messages',
        default=False)


class SubscriptionStats(Subscription):
    """Pub/Sub subscription statistics object model"""
    created: datetime = Field(
        description='Timestamp of connection creation'
    )
    last_poll: Optional[datetime] = Field(
        default=None,
        description='Timestamp when connection last polled for data'
    )


# User model definitions

class UserGroup(DatabaseModel):
    """API model to group associated user accounts"""
    name: str = Field(
        description="User group name"
    )

    @classmethod
    def get_indexes(cls):
        """Get an index to bind unique constraint to group name"""
        return [
            cls.Index('name', {'unique': True}),
        ]


class User(BeanieBaseUser, Document,  # pylint: disable=too-many-ancestors
           DatabaseModel):
    """API User model"""
    username: Annotated[str, Indexed(unique=True)]
    groups: List[UserGroup] = Field(
        default=[],
        description="A list of groups that the user belongs to"
    )

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = {group.name for group in groups}
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups

    class Settings(BeanieBaseUser.Settings):
        """Configurations"""
        # MongoDB collection name for model
        name = "user"

    @classmethod
    def get_indexes(cls):
        """Get indices"""
        return [
            cls.Index('email', {'unique': True}),
        ]

    @model_serializer(when_used='json')
    def serialize_model(self) -> Dict[str, Any]:
        """Serialize model by converting PyObjectId to string"""
        values = self.__dict__.copy()
        for field_name, value in values.items():
            if isinstance(value, PydanticObjectId):
                values[field_name] = str(value)
        return values


class UserRead(schemas.BaseUser[PydanticObjectId], ModelId):
    """Schema for reading a user"""
    username: Annotated[str, Indexed(unique=True)]
    groups: List[UserGroup] = Field(default=[])

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = {group.name for group in groups}
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups

    @model_serializer(when_used='json')
    def serialize_model(self) -> Dict[str, Any]:
        """Serialize model by converting PyObjectId to string"""
        values = self.__dict__.copy()
        for field_name, value in values.items():
            if isinstance(value, PydanticObjectId):
                values[field_name] = str(value)
        return values


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a user"""
    username: Annotated[str, Indexed(unique=True)]
    groups: List[str] = Field(default=[])

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = set(groups)
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating a user"""
    username: Annotated[Optional[str], Indexed(unique=True),
                        Field(default=None)]
    groups: List[str] = Field(default=[])

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = set(groups)
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups


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
