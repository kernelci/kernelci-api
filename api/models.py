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
from typing import Optional, TypeVar, List
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
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


# MongoDB-based durable Pub/Sub models
# Note: Event storage uses EventHistory model from kernelci-core
# (stored in 'eventhistory' collection with sequence_id, channel, owner fields)

class SubscriberState(BaseModel):
    """Tracks subscriber position for durable event delivery

    Only created when subscriber_id is provided during subscription.
    Enables catch-up on missed events after reconnection.
    """
    subscriber_id: str = Field(
        description='Unique subscriber identifier (client-provided)'
    )
    channel: str = Field(
        description='Subscribed channel name'
    )
    user: str = Field(
        description='Username of subscriber (for ownership validation)'
    )
    promiscuous: bool = Field(
        default=False,
        description='If true, receive all messages regardless of owner'
    )
    last_event_id: int = Field(
        default=0,
        description='Last acknowledged event ID (implicit ACK on next poll)'
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description='Subscription creation timestamp'
    )
    last_poll: Optional[datetime] = Field(
        default=None,
        description='Last poll timestamp (used for stale cleanup)'
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


class UserCreateRequest(schemas.BaseUserCreate):
    """Create user request schema for API router"""
    username: Annotated[str, Indexed(unique=True)]
    groups: List[str] = Field(default=[])

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = set(groups)
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups


class UserCreate(schemas.BaseUserCreate):
    """Schema used for sending create user request to 'fastapi-users' router"""
    username: Annotated[str, Indexed(unique=True)]
    groups: List[UserGroup] = Field(default=[])

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = {group.name for group in groups}
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups


class UserUpdateRequest(schemas.BaseUserUpdate):
    """Update user request schema for API router"""
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


class UserUpdate(schemas.BaseUserUpdate):
    """Schema used for sending update user request to 'fastapi-users' router"""
    username: Annotated[Optional[str], Indexed(unique=True),
                        Field(default=None)]
    groups: List[UserGroup] = Field(default=[])

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = {group.name for group in groups}
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups


# Invite-only user onboarding models

class UserInviteRequest(BaseModel):
    """Admin invite request schema for API router"""

    username: Annotated[str, Indexed(unique=True)]
    email: EmailStr
    groups: List[str] = Field(default=[])
    is_superuser: bool = False
    send_email: bool = True
    return_token: bool = False
    resend_if_exists: bool = False

    @field_validator('groups')
    def validate_groups(cls, groups):   # pylint: disable=no-self-argument
        """Unique group constraint"""
        unique_names = set(groups)
        if len(unique_names) != len(groups):
            raise ValueError("Groups must have unique names.")
        return groups


class InviteAcceptRequest(BaseModel):
    """Accept invite request schema for API router"""

    token: str
    password: str


class UserInviteResponse(BaseModel):
    """Invite response schema"""

    user: UserRead
    email_sent: bool
    public_base_url: str
    accept_invite_url: str
    invite_url: Optional[str] = None
    token: Optional[str] = None


class InviteUrlResponse(BaseModel):
    """Resolved public URL info for invite/accept endpoints"""

    public_base_url: str
    accept_invite_url: str


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
